"""Integrated invocation adapter for IBM Bob Shell 2.0 (D-04, F-02).

Joins Felipe's Bob integration and Daniel's deterministic pipeline:
- Safe invocation through subprocess with an explicit argument list (no shell=True).
- Prompt passed on stdin, so it can never inject CLI flags.
- BOB_API_KEY read from environment variables (or a local .env).
- Resource control: timeout per stage, cost cap and turn cap.
- Three transparent execution modes (rule D8):
    1. 'live': direct invocation of the Bob Shell 2.0.5 CLI with the configured API key.
    2. 'imported': loads a previously recorded Bob session (JSON).
    3. 'example': deterministic fallback based on real AST facts and evaluation/.
- Fully compatible with the unit tests for the Bob assets and custom modes.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BUILTIN_MODES: frozenset[str] = frozenset({"agent", "plan", "ask"})
DEFAULT_TIMEOUT_S = 600
DEFAULT_MAX_TURNS = 30
DEFAULT_MAX_COST = 5.0
REPO_ROOT = Path(__file__).resolve().parents[3]
CUSTOM_MODES_FILE = REPO_ROOT / ".bob" / "custom_modes.yaml"
_SLUG_PATTERN = re.compile(r"^\s*-\s*slug:\s*([a-z0-9-]+)\s*$", re.MULTILINE)
_STDERR_TAIL_CHARS = 2000
# Variables that never reach the Bob process: a subagent or a tool cannot leak what it never receives.
_SECRET_ENV_NAME = re.compile(r"TOKEN|SECRET|PASSW|PRIVATE|CREDENTIAL|API_?KEY|ACCESS_KEY", re.IGNORECASE)

ExecutionMode = Literal["live", "imported", "example"]

# Running Bob processes: the server terminates them on shutdown so no orphan session keeps
# spending bobcoins with nobody reading its output.
_ACTIVE_PROCESSES: set[subprocess.Popen] = set()
_ACTIVE_LOCK = threading.Lock()


# Events Bob writes only to its log (not to stdout with stream-json) and that happen in real time.
LOG_ONLY_EVENTS = frozenset({"cost", "subagent_start", "subagent_end"})
LOG_DISCOVERY_S = 20.0
LOG_POLL_S = 0.5


class BobLogTail(threading.Thread):
    """Follows the log of THIS Bob session to receive, in real time, the subagent lifecycle and
    the cost per turn (with stream-json those events only go to the log).

    Best effort: if it cannot find the log (another Bob version, another HOME), it emits nothing.
    """

    def __init__(self, workspace: Path, since: float, on_event: Callable[[dict[str, Any]], None],
                 log_dir: Path | None = None) -> None:
        super().__init__(daemon=True)
        self.workspace = str(workspace)
        self.since = since
        self.on_event = on_event
        self.log_dir = log_dir or Path(os.environ.get("BOB_LOG_DIR", Path.home() / ".bob" / "logs" / "shell"))
        self._stop_event = threading.Event()
        self.found: Path | None = None

    def stop(self) -> None:
        self._stop_event.set()
        self.join(timeout=3)

    def _discover(self) -> Path | None:
        if not self.log_dir.is_dir():
            return None
        candidates = sorted(self.log_dir.glob("bob-shell-*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in candidates[:8]:
            try:
                if path.stat().st_mtime < self.since - 1:
                    continue
                with path.open(encoding="utf-8", errors="replace") as handle:
                    head = handle.read(200_000)
                escaped_ws = json.dumps(self.workspace).strip('"')
                if self.workspace in head or escaped_ws in head or self.workspace.replace("\\", "/") in head:
                    return path
            except OSError:
                continue
        return None

    def run(self) -> None:
        deadline = time.monotonic() + LOG_DISCOVERY_S
        while not self._stop_event.is_set() and self.found is None and time.monotonic() < deadline:
            self.found = self._discover()
            if self.found is None:
                self._stop_event.wait(LOG_POLL_S)
        if self.found is None:
            self.found = self._discover()  # very short sessions: one last try before giving up
        if self.found is None:
            return
        with self.found.open(encoding="utf-8", errors="replace") as handle:
            while True:
                line = handle.readline()
                if line:
                    self._handle_line(line)
                    continue
                if self._stop_event.is_set():
                    break
                self._stop_event.wait(LOG_POLL_S)

    def _handle_line(self, line: str) -> None:  # not `_handle`: threading.Thread owns that name (Python 3.13+)
        try:
            record = json.loads(line)
            if not str(record.get("module", "")).endswith("json-renderer"):
                return
            event = json.loads(record.get("msg", ""))
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(event, dict) or event.get("type") not in LOG_ONLY_EVENTS:
            return
        stamp = str(record.get("ts", ""))
        try:
            if datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() < self.since - 1:
                return  # history of a resumed session
        except ValueError:
            return
        event["timestamp"] = stamp
        try:
            self.on_event(event)
        except Exception:  # noqa: BLE001 - the UI never brings the audit down
            logger.exception("Error processing an event from the Bob log")


def terminate_active_sessions() -> int:
    """Terminates every running Bob session. Returns how many there were."""
    with _ACTIVE_LOCK:
        processes = list(_ACTIVE_PROCESSES)
    for process in processes:
        if process.poll() is None:
            process.kill()
    return len(processes)


class BobError(RuntimeError):
    """Base error of the Bob integration."""


class BobNotInstalledError(BobError):
    """The Bob Shell executable was not found."""


class BobConfigError(BobError):
    """Invalid configuration: missing API key or unknown mode."""


class BobTimeoutError(BobError):
    """Bob did not finish within the allowed time."""


class BobExecutionError(BobError):
    """Bob exited with an error or its output is not a valid result."""


class BobBudgetError(BobError):
    """The server reached its daily bobcoin spending limit (BOB_DAILY_SPEND_LIMIT)."""


BUDGET_MESSAGE = (
    "The server reached today's bobcoin limit for live features. The recorded FacturaYa showcase still works; "
    "try live features again tomorrow."
)


class BobStats(BaseModel):
    task_id: str
    duration_ms: int
    session_costs: float
    tool_calls: int = 0


class BobResult(BaseModel):
    mode: str
    status: str
    last_message: str
    stats: BobStats | None = None
    execution_mode: ExecutionMode


# Daily spending guard for a public deployment without LIVE_AUDIT_TOKEN. Keyed by Bob task id, so a
# resumed session (whose session_costs are cumulative) is counted once. Kept in memory: it resets at
# UTC midnight and when the process restarts. Unset limit = no guard.
_SPEND_LOCK = threading.Lock()
_SPENT_BY_TASK: dict[str, tuple[str, float]] = {}


def daily_spend_limit() -> float | None:
    """BOB_DAILY_SPEND_LIMIT in bobcoins, or None when unset or invalid."""
    raw = os.environ.get("BOB_DAILY_SPEND_LIMIT", "").strip()
    try:
        value = float(raw) if raw else 0.0
    except ValueError:
        return None
    return value if value > 0 else None


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def spent_today() -> float:
    """Bobcoins this process has spent on Bob sessions today (UTC)."""
    today = _today()
    with _SPEND_LOCK:
        return round(sum(cost for day, cost in _SPENT_BY_TASK.values() if day == today), 4)


def record_spend(result: "BobResult") -> None:
    """Records a finished session's cost for the daily guard."""
    if not result.stats:
        return
    with _SPEND_LOCK:
        _, previous = _SPENT_BY_TASK.get(result.stats.task_id, (_today(), 0.0))
        _SPENT_BY_TASK[result.stats.task_id] = (_today(), max(previous, result.stats.session_costs))


def bob_child_env() -> dict[str, str]:
    """Environment of the Bob process: the server's, without the application's secrets.

    Bob only needs its own (`BOB_*`, e.g. BOB_API_KEY). LIVE_AUDIT_TOKEN and any other key are
    removed: even if a repository got Bob to run something, there would be no credentials to leak.
    """
    env = {
        key: value for key, value in os.environ.items()
        if key.upper().startswith("BOB") or not _SECRET_ENV_NAME.search(key)
    }
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


class BobRunSettings(BaseModel):
    bob_binary: str = "bob"
    timeout_s: int = Field(default=DEFAULT_TIMEOUT_S, gt=0)
    max_turns: int = Field(default=DEFAULT_MAX_TURNS, gt=0)
    max_cost: float = Field(default=DEFAULT_MAX_COST, gt=0)
    disable_mcp: bool = True
    disable_subagents: bool = False
    accept_license: bool = True

    @classmethod
    def from_env(cls) -> "BobRunSettings":
        """Reads optional overrides from environment variables."""
        overrides: dict[str, object] = {}
        env_map = {
            "BOB_BINARY": "bob_binary",
            "BOB_TIMEOUT_S": "timeout_s",
            "BOB_MAX_TURNS": "max_turns",
            "BOB_MAX_COST": "max_cost",
        }
        for env_name, field_name in env_map.items():
            value = os.environ.get(env_name)
            if value:
                overrides[field_name] = value
        if os.environ.get("BOB_ACCEPT_LICENSE", "").lower() == "true":
            overrides["accept_license"] = True
        return cls.model_validate(overrides)


def load_custom_mode_slugs(modes_file: Path = CUSTOM_MODES_FILE) -> frozenset[str]:
    """Extracts the slugs from `.bob/custom_modes.yaml` without depending on PyYAML."""
    if not modes_file.is_file():
        return frozenset()
    return frozenset(_SLUG_PATTERN.findall(modes_file.read_text(encoding="utf-8")))


def _result_payloads(stdout: str) -> list[dict]:
    """JSON candidates: the whole document (exported with indentation) or one line per event."""
    candidates = [stdout.strip(), *reversed(stdout.strip().splitlines())]
    payloads: list[dict] = []
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("type") == "result":
            payloads.append(payload)
    return payloads


def parse_bob_output(stdout: str, mode: str) -> BobResult:
    """Finds the last `result` event in the JSON output of `bob run --format json`."""
    payloads = _result_payloads(stdout)
    if not payloads:
        raise BobExecutionError("Bob's output has no JSON 'result' event.")
    payload = payloads[0]
    return BobResult(
        mode=mode,
        status=payload.get("status", "unknown"),
        last_message=payload.get("last_message", ""),
        stats=BobStats.model_validate(payload["stats"]) if "stats" in payload else None,
        execution_mode="live",
    )


def get_bob_api_key() -> str:
    """Gets the IBM Bob API key configured in the environment."""
    return os.environ.get("BOB_API_KEY", "").strip()


def is_bob_cli_available() -> bool:
    """Checks whether the Bob Shell 2.0 binary is installed on the system PATH."""
    return (shutil.which("bob") is not None) or (shutil.which("bob.cmd") is not None)


def determine_operational_mode() -> str:
    """Determines the execution mode dynamically, following architecture rule D8."""
    forced_mode = os.environ.get("LEGACYLENS_EXECUTION_MODE", "").lower().strip()
    if forced_mode in ["live", "imported", "example"]:
        return forced_mode

    api_key = get_bob_api_key()
    cli_available = is_bob_cli_available()

    if api_key and cli_available:
        return "live"

    imported_dir = REPO_ROOT / "bob-sessions"
    if imported_dir.exists() and any(imported_dir.glob("*.json")):
        return "imported"

    return "example"


class BobAdapter:
    """Unified execution adapter for IBM Bob Shell 2.0."""

    def __init__(
        self,
        workspace: Optional[Path | str] = None,
        settings: BobRunSettings | None = None,
        allowed_modes: frozenset[str] | None = None,
        mode: Optional[str] = None,
        workspace_dir: Optional[Path | str] = None,
        requested_mode: Optional[str] = None,
    ) -> None:
        raw_ws = workspace or workspace_dir or REPO_ROOT
        self.workspace = Path(raw_ws).resolve()
        self.workspace_dir = self.workspace
        self.settings = settings or BobRunSettings.from_env()
        custom = load_custom_mode_slugs() if allowed_modes is None else allowed_modes
        self.allowed_modes = BUILTIN_MODES | custom
        self.mode = mode or requested_mode or determine_operational_mode()
        self.api_key = get_bob_api_key()

    def build_command(
        self,
        mode: str,
        binary_path: str,
        settings: "BobRunSettings | None" = None,
        output_format: str = "json",
        resume_task_id: str | None = None,
    ) -> list[str]:
        """Builds the argument list; the prompt is never part of it."""
        settings = settings or self.settings
        command = [
            binary_path,
            "run",
            "--format", output_format,
            "--mode", mode,
            "--workspace", str(self.workspace),
            "--max-turns", str(settings.max_turns),
            "--max-cost", str(settings.max_cost),
            "--trust",
        ]
        if resume_task_id:
            command += ["--resume", resume_task_id]
        if settings.disable_mcp:
            command.append("--disable-mcp")
        if settings.disable_subagents:
            command.append("--disable-subagents")
        if settings.accept_license:
            command.append("--accept-license")
        return command

    def _validate(self, mode: str, prompt: str) -> str:
        if mode not in self.allowed_modes:
            raise BobConfigError(f"Bob mode not allowed: {mode!r}")
        if not prompt.strip():
            raise BobConfigError("The prompt for Bob is empty.")
        if not os.environ.get("BOB_API_KEY"):
            raise BobConfigError("BOB_API_KEY is missing from the environment (see .env.example).")
        if not self.workspace.is_dir():
            raise BobConfigError(f"The workspace does not exist: {self.workspace}")
        limit = daily_spend_limit()
        if limit is not None and spent_today() >= limit:
            raise BobBudgetError(f"Daily bobcoin limit reached ({spent_today():.2f} of {limit:g}).")
        binary_path = shutil.which(self.settings.bob_binary)
        if binary_path is None:
            raise BobNotInstalledError(
                f"'{self.settings.bob_binary}' was not found. Install Bob Shell (see docs/bob-usage.md)."
            )
        return binary_path

    def run(self, mode: str, prompt: str) -> BobResult:
        """Runs a mode with the prompt on stdin and returns the `live` result."""
        binary_path = self._validate(mode, prompt)
        command = self.build_command(mode, binary_path)
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",  # Bob emits UTF-8; without this Windows decodes with cp1252 and corrupts accents
                errors="replace",
                timeout=self.settings.timeout_s,
                cwd=self.workspace,
                env=bob_child_env(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BobTimeoutError(
                f"Bob ({mode}) exceeded the {self.settings.timeout_s}s timeout."
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout)[-_STDERR_TAIL_CHARS:].strip()
            raise BobExecutionError(
                f"Bob ({mode}) exited with code {completed.returncode}: {detail}"
            )
        result = parse_bob_output(completed.stdout, mode)
        record_spend(result)
        if result.status != "success":
            raise BobExecutionError(f"Bob ({mode}) returned status {result.status!r}.")
        return result

    def run_stream(
        self,
        mode: str,
        prompt: str,
        on_event: Callable[[dict[str, Any]], None],
        settings: "BobRunSettings | None" = None,
        resume_task_id: str | None = None,
        raw_log: Path | None = None,
    ) -> BobResult:
        """Runs `bob run --format stream-json` and hands each event to `on_event` as it happens.

        With `resume_task_id`, Bob first replays the session history: those events are dropped
        until the user message carrying this prompt shows up. The final message is rebuilt from the
        assistant text after the last tool call (stream-json carries no `last_message`).
        """
        settings = settings or self.settings
        binary_path = self._validate(mode, prompt)
        command = self.build_command(mode, binary_path, settings, "stream-json", resume_task_id)
        started_at = time.time()
        child_env = bob_child_env()
        process = subprocess.Popen(  # noqa: S603 - argument list, no shell
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=self.workspace,
            env=child_env,
        )
        with _ACTIVE_LOCK:
            _ACTIVE_PROCESSES.add(process)
        raw_lock = threading.Lock()
        raw_handle = raw_log.open("a", encoding="utf-8") if raw_log else None

        def record(event: dict[str, Any]) -> None:
            if raw_handle:
                with raw_lock:
                    raw_handle.write(json.dumps(event, ensure_ascii=False) + "\n")

        def from_log(event: dict[str, Any]) -> None:
            record(event)
            on_event(event)

        tail = BobLogTail(self.workspace, started_at, from_log)
        tail.start()
        timed_out = threading.Event()

        def kill() -> None:
            timed_out.set()
            process.kill()

        timer = threading.Timer(settings.timeout_s, kill)
        timer.start()
        stderr_parts: list[str] = []
        drain = threading.Thread(target=lambda: stderr_parts.append(process.stderr.read()), daemon=True)
        drain.start()
        replaying = bool(resume_task_id)
        marker = " ".join(prompt.split())[:60]
        text: list[str] = []
        final: dict[str, Any] | None = None
        try:
            assert process.stdin is not None and process.stdout is not None
            stdin = process.stdin

            def feed_prompt() -> None:
                # In its own thread: if Bob writes before reading the whole prompt, nobody blocks.
                try:
                    stdin.write(prompt)
                    stdin.close()
                except (BrokenPipeError, OSError, ValueError):
                    logger.debug("Bob closed stdin before reading the whole prompt")

            threading.Thread(target=feed_prompt, name="bob-stdin", daemon=True).start()
            for line in process.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if replaying:
                    if event.get("type") == "message" and event.get("role") == "user" \
                            and " ".join(str(event.get("content", "")).split()).startswith(marker):
                        replaying = False
                    continue
                record(event)
                if event.get("type") == "message" and event.get("role") == "assistant":
                    text.append(str(event.get("content", "")))
                elif event.get("type") == "tool_use":
                    text = []
                elif event.get("type") == "result":
                    final = event
                try:
                    on_event(event)
                except Exception:  # noqa: BLE001 - the UI must never bring an audit down
                    logger.exception("Error processing a Bob event")
            process.wait()
        finally:
            timer.cancel()
            tail.stop()
            with _ACTIVE_LOCK:
                _ACTIVE_PROCESSES.discard(process)
            if process.poll() is None:
                process.kill()  # e.g. an exception in the reader: never leave Bob running alone
            drain.join(timeout=2)
            if raw_handle:
                with raw_lock:
                    raw_handle.close()
        if timed_out.is_set():
            raise BobTimeoutError(f"Bob ({mode}) exceeded the {settings.timeout_s}s timeout.")
        if process.returncode != 0:
            detail = ("".join(stderr_parts))[-_STDERR_TAIL_CHARS:].strip()
            raise BobExecutionError(f"Bob ({mode}) exited with code {process.returncode}: {detail}")
        if final is None:
            raise BobExecutionError("Bob's output has no 'result' event.")
        result = BobResult(
            mode=mode,
            status=final.get("status", "unknown"),
            last_message="".join(text).strip(),
            stats=BobStats.model_validate(final["stats"]) if "stats" in final else None,
            execution_mode="live",
        )
        record_spend(result)
        if result.status != "success":
            raise BobExecutionError(f"Bob ({mode}) returned status {result.status!r}.")
        return result

    def find_session_id(self) -> str | None:
        """Latest root Bob session in this workspace, read-only from its local database.

        Used to resume a session whose stream was cut before the `result` event (e.g.
        `read ETIMEDOUT` from the inference service). It is a best-effort rescue: if the database
        does not exist or its schema changes, it returns None and the original error is reported.
        """
        database = Path(os.environ.get("BOB_DB_PATH", Path.home() / ".bob" / "db" / "bob.db"))
        if not database.is_file():
            return None
        try:
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=2) as connection:
                row = connection.execute(
                    "SELECT id FROM tasks WHERE parent_id IS NULL AND json_extract(env, '$.workspace') = ? "
                    "ORDER BY created_at DESC LIMIT 1",
                    (str(self.workspace),),
                ).fetchone()
        except sqlite3.Error:
            logger.warning("Could not read the Bob session database", exc_info=True)
            return None
        return str(row[0]) if row else None

    @staticmethod
    def import_result(json_path: Path, mode: str) -> BobResult:
        """Assisted mode (D12): loads an exported Bob result as `imported`."""
        result = parse_bob_output(json_path.read_text(encoding="utf-8"), mode)
        return result.model_copy(update={"execution_mode": "imported"})

