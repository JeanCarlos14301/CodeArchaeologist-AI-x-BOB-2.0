"""Activity log of an analysis: what each stage does while it happens.

- `EventLog` writes events (JSONL) to `artifacts/jobs/<id>/events.jsonl`; the API serves them by cursor.
- `BobActivity` turns the `bob run --format stream-json` stream into readable events: plan (todo list),
  tools, delegation to subagents, reasoning, turns and cost.
- `inventory_events` describes the sandbox (languages, lines, folders) without running anything.

Events are a sanitized summary: they never include the content of the files Bob reads, and absolute
server paths become paths relative to the repository.
"""

import json
import re
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

EVENTS_FILE = "events.jsonl"
Stage = Literal["preparing", "auditing", "validating", "migration", "done"]

MAX_TITLE = 200
MAX_DETAIL = 600
MAX_THINKING = 480
MAX_EVENTS_PER_PAGE = 400
MAX_EVENTS = 5000  # cap per analysis: above it only essential events are recorded
MAX_TODOS = 40
ESSENTIAL_KINDS = frozenset({"stage.start", "pipeline.failed", "bob.result", "bob.finalize", "evidence.summary",
                             "tests.summary", "tests.skipped", "dossier.ready"})
_SEQ_PREFIX = re.compile(r'^\{"seq":(\d+),')
# Absolute POSIX or Windows paths (not URLs): reduced to their last component.
_ABSOLUTE_PATH = re.compile(r"(?<![\w.:/])/(?:[^\s/\"'`<>|:]+/)+([^\s/\"'`<>|:]*)|\b[A-Za-z]:\\(?:[^\s\\\"'`<>|]+\\)*([^\s\\\"'`<>|]*)")
WRITING_STEP = 2000  # how many characters of the final JSON between progress reports
_TODO = re.compile(r"^\s*\[( |x|X|-)\]\s*(.+?)\s*$")
_TASK_TAGS = re.compile(r"</?task_result>")
MAX_REPORT = 220
_WHITESPACE = re.compile(r"\s+")
# Extensions counted as code in the inventory (the rest is grouped as "other").
LANGUAGES = {
    ".py": "Python", ".sql": "SQL", ".html": "HTML", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".css": "CSS", ".md": "Markdown", ".json": "JSON",
    ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML", ".ini": "INI", ".txt": "Text",
}


class PipelineEvent(BaseModel):
    seq: int
    t: float = Field(description="Seconds since the start of the analysis.")
    stage: Stage
    kind: str
    actor: str
    title: str
    detail: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    recorded: bool = False


def redact_paths(text: str) -> str:
    """Never exposes server paths: any absolute path keeps only its final name."""
    return _ABSOLUTE_PATH.sub(lambda match: match.group(1) or match.group(2) or "…", text)


def _clip(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    text = _WHITESPACE.sub(" ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


class EventLog:
    """Append-only, thread-safe log. One JSONL file per analysis."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._started = time.monotonic()
        self._offset = 0.0
        self._seq = self._last_seq()

    def _last_seq(self) -> int:
        if not self.path.is_file():
            return 0
        last = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                last = max(last, int(json.loads(line)["seq"]))
            except (ValueError, KeyError, json.JSONDecodeError):
                continue
        return last

    def now(self) -> float:
        return round(time.monotonic() - self._started + self._offset, 3)

    def advance(self, seconds: float) -> None:
        """Shifts the clock (when a recorded session is inserted, what follows goes after it)."""
        with self._lock:
            self._offset += max(0.0, seconds)

    def emit(self, stage: Stage, kind: str, actor: str, title: str, detail: str | None = None,
             data: dict[str, Any] | None = None, t: float | None = None, recorded: bool = False) -> PipelineEvent | None:
        with self._lock:
            if self._seq >= MAX_EVENTS and kind not in ESSENTIAL_KINDS:
                return None  # anomalous session: the file never grows without bound
            self._seq += 1
            event = PipelineEvent(
                seq=self._seq, t=self.now() if t is None else round(t, 3), stage=stage, kind=kind, actor=actor,
                title=_clip(title, MAX_TITLE) or "", detail=_clip(detail, MAX_DETAIL), data=data or {}, recorded=recorded,
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json() + "\n")
        return event


# Where to resume reading each log: (seq of the last delivered event, next byte). Polls always
# ask with `after` = the last thing they received, so only what was appended since then is read.
_TAIL_LOCK = threading.Lock()
_TAILS: dict[str, tuple[int, int]] = {}
_MAX_TAILS = 512


def _remember_tail(key: str, seq: int, position: int) -> None:
    with _TAIL_LOCK:
        _TAILS.pop(key, None)
        _TAILS[key] = (seq, position)
        while len(_TAILS) > _MAX_TAILS:
            _TAILS.pop(next(iter(_TAILS)))


def read_events(path: Path, after: int = 0, limit: int = MAX_EVENTS_PER_PAGE) -> list[PipelineEvent]:
    """Events with `seq > after`, in order. Skips corrupt lines and leaves a half-written one for the next poll."""
    if not path.is_file():
        return []
    key = str(path.resolve())
    with _TAIL_LOCK:
        cached = _TAILS.get(key)
    size = path.stat().st_size
    position = cached[1] if cached and cached[0] == after and cached[1] <= size else 0
    events: list[PipelineEvent] = []
    with path.open("rb") as handle:
        handle.seek(position)
        for raw in handle:
            if not raw.endswith(b"\n"):
                break  # another thread is writing it right now: it is delivered whole on the next poll
            position += len(raw)
            line = raw.decode("utf-8", errors="replace").strip()
            prefix = _SEQ_PREFIX.match(line)
            if prefix and int(prefix.group(1)) <= after:
                continue  # already delivered: not validated again on every poll
            try:
                event = PipelineEvent.model_validate_json(line)
            except ValueError:
                continue
            if event.seq > after:
                events.append(event)
            if len(events) >= limit:
                break
    _remember_tail(key, events[-1].seq if events else after, position)
    return events


# --- Sandbox inventory --------------------------------------------------------------------

def inventory_events(workspace: Path) -> dict[str, Any]:
    """Measurable summary of the repository copied to the sandbox (without the .bob/ configuration)."""
    languages: Counter[str] = Counter()
    python_lines = 0
    files = 0
    total_bytes = 0
    top_dirs: Counter[str] = Counter()
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace)
        if relative.parts[0] == ".bob":
            continue
        files += 1
        total_bytes += path.stat().st_size
        languages[LANGUAGES.get(path.suffix.lower(), "Other")] += 1
        top_dirs[relative.parts[0] if len(relative.parts) > 1 else "(root)"] += 1
        if path.suffix.lower() == ".py":
            try:
                python_lines += sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return {
        "files": files,
        "bytes": total_bytes,
        "python_lines": python_lines,
        "languages": [{"name": name, "files": count} for name, count in languages.most_common(8)],
        "top_dirs": [{"name": name, "files": count} for name, count in top_dirs.most_common(8)],
    }


# --- Bob stream ---------------------------------------------------------------------------

def relative_to_workspace(value: str, workspace: Path) -> str:
    """Never exposes server paths: relative to the repo, or only the name when outside it."""
    text = value.strip()
    root = str(workspace.resolve())
    if text.startswith(root):
        text = text[len(root):].lstrip("/\\") or "."
    elif text.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", text):
        text = Path(text).name
    return text.replace("\\", "/")


def _strip_paths(text: str, workspace: Path) -> str:
    root = str(workspace.resolve())
    return redact_paths(text.replace(root + "\\", "").replace(root + "/", "").replace(root, "."))


def parse_todos(raw: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for line in raw.splitlines()[:MAX_TODOS * 4]:
        if len(items) >= MAX_TODOS:
            break
        match = _TODO.match(line)
        if match:
            mark = match.group(1).lower()
            state = "done" if mark == "x" else "active" if mark == "-" else "pending"
            items.append({"state": state, "text": _clip(match.group(2), 160) or ""})
    return items


class BobActivity:
    """Turns raw Bob events (stream-json) into events of the `auditing` stage.

    The interpreter is content-free: it never stores tool outputs or code it read.
    """

    ORCHESTRATOR = "evidence-auditor"

    def __init__(self, log: EventLog, workspace: Path, actor: str = ORCHESTRATOR,
                 recorded: bool = False, clock: float | None = None) -> None:
        self.log = log
        self.workspace = workspace
        self.actor = actor
        self.recorded = recorded
        self.clock = clock
        self._text: list[str] = []
        self._chars = 0
        self._reported = 0
        self._turn = 0
        self._last_tokens: tuple[int, int] | None = None
        self._first_ts: float | None = None
        self._spawned: dict[str, str] = {}
        # The stream (stdout) and the Bob log (real time) arrive from different threads.
        self._lock = threading.Lock()

    def _t(self, raw: dict[str, Any]) -> float | None:
        """In a recorded session the original pace is kept, starting from `clock`."""
        if self.clock is None:
            return None
        try:
            seconds = datetime.fromisoformat(str(raw.get("timestamp", "")).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
        if self._first_ts is None:
            self._first_ts = seconds
        return self.clock + (seconds - self._first_ts)

    def _emit(self, raw: dict[str, Any], kind: str, title: str, detail: str | None = None, data: dict[str, Any] | None = None,
              actor: str | None = None) -> None:
        self.log.emit("auditing", kind, actor or self.actor, title, detail, data, t=self._t(raw), recorded=self.recorded)

    def flush_thinking(self, raw: dict[str, Any] | None = None) -> None:
        text = "".join(self._text).strip()
        self._text = []
        self._chars = 0
        self._reported = 0
        if not text:
            return
        if text.lstrip().startswith("{") or '"findings"' in text[:200]:
            self._emit(raw or {}, "bob.answer", "Bob delivered the dossier", data={"chars": len(text)})
            return
        self._emit(raw or {}, "bob.thinking", "Reasoning", _clip(_strip_paths(text, self.workspace), MAX_THINKING))

    def feed(self, raw: dict[str, Any]) -> None:
        with self._lock:
            self._feed(raw)

    def _feed(self, raw: dict[str, Any]) -> None:
        kind = raw.get("type")
        if kind == "message" and raw.get("role") == "assistant":
            chunk = str(raw.get("content", ""))
            self._text.append(chunk)
            self._chars += len(chunk)
            # Writing the dossier can take minutes: progress is reported without exposing the text.
            if self._chars - self._reported >= WRITING_STEP and "".join(self._text).lstrip().startswith("{"):
                self._reported = self._chars - self._chars % WRITING_STEP
                self._emit(raw, "bob.writing", "Bob is writing the dossier", data={"chars": self._reported})
        elif kind == "tool_use":
            self.flush_thinking(raw)
            self._tool(raw)
        elif kind == "tool_result" and str(raw.get("tool_id")) in self._spawned:
            self._report(raw)
        elif kind == "tool_result" and raw.get("status") not in (None, "success"):
            self._emit(raw, "bob.tool.error", "A tool failed", _clip(_strip_paths(str(raw.get("output", "")), self.workspace), 160))
        elif kind == "subagent_start":
            agent = str(raw.get("agentType", "subagent"))
            task = _clip(_strip_paths(str(raw.get("description", "")), self.workspace), 280)
            self._emit(raw, "bob.subagent.start", f"Delegated to {agent}", task, {"agent": agent})
        elif kind == "subagent_end":
            meta = raw.get("metadata") or {}
            agent = str(meta.get("agentType", "subagent"))
            spend = meta.get("spend") or {}
            self._emit(raw, "bob.subagent.end", f"{agent} finished", data={
                "agent": agent,
                "tool_uses": meta.get("toolUseCount"),
                "turns": meta.get("loopTurnCount"),
                "duration_ms": meta.get("durationMs"),
                "cost": spend.get("cost"),
                "exit": meta.get("loopExitReason"),
            })
        elif kind == "cost":
            costs = raw.get("costs") or {}
            tokens = (int(costs.get("input", 0) or 0), int(costs.get("output", 0) or 0))
            if tokens != self._last_tokens:
                self._last_tokens = tokens
                self._turn += 1
                self._emit(raw, "bob.turn", f"Orchestrator turn {self._turn}",
                           data={"turn": self._turn, "input_tokens": tokens[0], "output_tokens": tokens[1]})
        elif kind == "result":
            self.flush_thinking(raw)
            stats = raw.get("stats") or {}
            self._emit(raw, "bob.result", "Bob session closed", data={
                "status": raw.get("status"),
                "cost": stats.get("session_costs"),
                "max_cost": stats.get("max_cost"),
                "duration_ms": stats.get("duration_ms"),
                "tool_calls": stats.get("tool_calls"),
            })

    def _report(self, raw: dict[str, Any]) -> None:
        """Report a subagent hands back to the orchestrator: first sentence and size, never the full text."""
        agent = self._spawned.pop(str(raw.get("tool_id")))
        output = _TASK_TAGS.sub("", str(raw.get("output", ""))).strip()
        first = re.split(r"(?<=[.!?])\s|\n", output, maxsplit=1)[0] if output else ""
        self._emit(raw, "bob.subagent.report", f"{agent} handed its report to the orchestrator",
                   _clip(_strip_paths(first, self.workspace), MAX_REPORT),
                   {"agent": agent, "chars": len(output), "status": raw.get("status")}, actor=agent)

    def _tool(self, raw: dict[str, Any]) -> None:
        name = str(raw.get("tool_name", "tool"))
        params = raw.get("parameters") or {}
        path = relative_to_workspace(str(params.get("path", "")), self.workspace) if params.get("path") else None
        if name == "update_todo_list":
            items = parse_todos(_strip_paths(str(params.get("todos", "")), self.workspace))
            active = next((item["text"] for item in items if item["state"] == "active"), None)
            self._emit(raw, "bob.plan", "Bob updated its plan", active, {"items": items})
        elif name == "spawn_subagent":
            # The real-time start arrives from the Bob log (subagent_start); here the tool_id is only
            # linked so the report the subagent returns to the orchestrator can be recognized later.
            self._spawned[str(raw.get("tool_id"))] = str(params.get("name", "subagent"))
        elif name == "use_skill":
            skill = str(params.get("skill_name", ""))
            self._emit(raw, "bob.skill", f"Activated the {skill} skill", data={"skill": skill})
        elif name == "read_file":
            self._emit(raw, "bob.tool", f"Read {path}", data={"tool": name, "target": path})
        elif name == "list_files":
            self._emit(raw, "bob.tool", f"Listed {path or '.'}", data={"tool": name, "target": path or "."})
        elif name == "glob":
            pattern = _clip(str(params.get("pattern", "")), 120)
            self._emit(raw, "bob.tool", f"Searched files {pattern}", data={"tool": name, "target": pattern})
        elif name in ("search_files", "grep", "codebase_search"):
            query = _clip(str(params.get("regex") or params.get("query") or params.get("pattern") or ""), 120)
            self._emit(raw, "bob.tool", f"Searched «{query}»" + (f" in {path}" if path else ""), data={"tool": name, "target": query})
        elif name in ("write_to_file", "apply_diff", "insert_content", "search_and_replace", "edit_file", "edit"):
            self._emit(raw, "bob.edit", f"Wrote {path}" if name == "write_to_file" else f"Edited {path}", data={"tool": name, "target": path})
        else:
            self._emit(raw, "bob.tool", f"Used {name}", data={"tool": name, "target": path})
