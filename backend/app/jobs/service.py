"""Audit service: runs the pipeline in a worker and exposes results and source code.

Only registered samples are audited (no arbitrary client paths) and only one `live` audit
can run at a time, to bound bobcoin spending.
"""

import io
import logging
import os
import shutil
import subprocess
import threading
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel

from app.adapters.bob_adapter import CUSTOM_MODES_FILE, REPO_ROOT, BobRunSettings, load_custom_mode_slugs
from app.contracts.schema_v1 import Dossier
from app.jobs.store import ExecutionMode, Job, JobStore
from app.pipeline.activity import EVENTS_FILE, EventLog, redact_paths
from app.pipeline.evidence_audit import DOSSIER_FILE, AuditError, run_evidence_audit
from app.modernization.implement import COPY_IGNORE
from app.modernization.studio import default_adapter
from app.pipeline.ingestion import (
    MAX_FILES_COUNT,
    MAX_UNCOMPRESSED_BYTES,
    MODERNIZE_MAX_FILES,
    MAX_ZIP_COMPRESSED_BYTES,
    IngestionSecurityError,
    validate_and_extract_zip,
)
from app.validators.evidence import resolve_inside

logger = logging.getLogger(__name__)

SAMPLES: dict[str, Path] = {
    "facturaya-v1": REPO_ROOT / "samples" / "facturaya-v1",
}
FIXTURES_DIR = REPO_ROOT / "contracts" / "fixtures"
# Showcase: a real Bob session recorded with stream-json (result + activity of the same session).
# `bob-evidence-auditor-facturaya.json` (25-09 session, no activity) is kept for the evaluation.
IMPORTED_FIXTURES: dict[str, Path] = {
    "facturaya-v1": FIXTURES_DIR / "bob-session-facturaya.json",
}
# Real recorded activity of the same Bob session (sanitized stream-json), for replay.
IMPORTED_EVENTS: dict[str, Path] = {
    "facturaya-v1": FIXTURES_DIR / "bob-events-facturaya.jsonl",
}
# Provenance of the versioned recording. It matches the session documented in
# docs/bob-usage.md; it is never replaced with the time a visitor opens it.
IMPORTED_RECORDED_AT: dict[str, str] = {
    "facturaya-v1": "2026-09-26T00:27:50-05:00",
}
EXAMPLE_DOSSIER = FIXTURES_DIR / "dossier-example.json"
MAX_SOURCE_LINES = 400
MAX_SOURCE_BYTES = 2_000_000
# `bob --version` starts the Node CLI: ~0.4 s locally, ~15 s on the Render instance.
BOB_VERSION_TIMEOUT_S = 45


STAGE_LABELS: dict[str, str] = {
    "preparing": "Indexing repository",
    "auditing": "Bob analyzes the code",
    "validating": "Verifying evidence",
    "migration": "Testing the first cut",
    "done": "Dossier ready",
}


def _emit_zip_checks(events: EventLog, data: bytes, max_files: int = MAX_FILES_COUNT) -> None:
    """Security checks the ZIP has just passed (all already enforced in ingestion.py)."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
    uncompressed = sum(member.file_size for member in members)
    checks = [
        ("Compressed size", f"{len(data) / 1024:.0f} KB", f"≤ {MAX_ZIP_COMPRESSED_BYTES // (1024 * 1024)} MB"),
        ("Entries in the ZIP", str(len(members)), f"≤ {max_files}"),
        ("Uncompressed size", f"{uncompressed / 1024:.0f} KB", f"≤ {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB (anti zip-bomb)"),
        ("Paths", "no «..» and no absolute paths", "anti ZipSlip"),
        ("Symbolic links", "none", "rejected"),
        ("Executable binaries", "none", "rejected"),
    ]
    for name, value, limit in checks:
        events.emit("preparing", "ingest.check", "python", name, None, {"value": value, "limit": limit, "status": "passed"})


class BusyError(RuntimeError):
    """A live audit is already running."""


class NotFoundError(LookupError):
    """Missing resource (job, sample or file)."""


class SourceLine(BaseModel):
    number: int
    text: str


class SourceExcerpt(BaseModel):
    path: str
    start: int
    end: int
    total_lines: int
    lines: list[SourceLine]


class BobStatus(BaseModel):
    installed: bool
    version: str | None
    api_key_configured: bool
    custom_modes: list[str]
    subagents: list[str]
    skills: list[str]
    max_cost_per_run: float
    timeout_s: int
    live_requires_token: bool


class AuditService:
    def __init__(self, store: JobStore, artifacts_dir: Path, executor: ThreadPoolExecutor) -> None:
        self._start_lock = threading.Lock()
        self.store = store
        self.artifacts_dir = artifacts_dir
        self.executor = executor
        # One showcase job per sample for the life of the process: the public, token-free showcase
        # must not let every click (or a bot) queue a new pytest run next to the live audits.
        self._showcase_jobs: dict[str, str] = {}

    def job_dir(self, job_id: str) -> Path:
        return self.artifacts_dir / job_id

    def start(self, sample: str, execution_mode: ExecutionMode) -> Job:
        if sample not in SAMPLES:
            raise NotFoundError(f"Unknown sample: {sample}")
        with self._start_lock:  # check and create atomically: never two live audits at once
            if execution_mode == "imported":
                reusable = self._reusable_showcase(sample)
                if reusable is not None:
                    return reusable
            if execution_mode == "live" and self.store.has_active("live"):
                raise BusyError("A live audit is already running; wait for it to finish.")
            job = self.store.create(sample, execution_mode)
            if execution_mode == "imported":
                self._showcase_jobs[sample] = job.id
        self.executor.submit(self._execute, job)
        return job

    def _reusable_showcase(self, sample: str) -> Job | None:
        """The current showcase job for a sample, unless it never started, vanished or failed."""
        job_id = self._showcase_jobs.get(sample)
        job = self.store.get(job_id) if job_id else None
        if job is None or job.status == "failed":
            return None
        return job

    def events(self, job_id: str) -> EventLog:
        return EventLog(self.job_dir(job_id) / EVENTS_FILE)

    def _stage_hook(self, job_id: str, events: EventLog) -> Callable[[str], None]:
        def on_stage(stage: str) -> None:
            self.store.update(job_id, stage=stage)
            events.emit(stage, "stage.start", "pipeline", STAGE_LABELS.get(stage, stage))  # type: ignore[arg-type]
        return on_stage

    def _fail(self, job: Job, events: EventLog, message: str) -> None:
        """Marks the failure while keeping the stage where it happened (the UI flags it with ✗).

        The message is published (feed and job): it never carries server paths.
        """
        message = redact_paths(message)
        stage = (self.store.get(job.id) or job).stage
        events.emit(stage if stage in STAGE_LABELS else "preparing", "pipeline.failed", "pipeline",  # type: ignore[arg-type]
                    "The analysis stopped", message)
        self.store.update(job.id, status="failed", error=message)

    def _execute(self, job: Job) -> None:
        self.store.update(job.id, status="running", stage="preparing")
        events = self.events(job.id)
        try:
            if job.execution_mode == "example":
                self._materialize_example(job)
            else:
                imported = IMPORTED_FIXTURES[job.sample] if job.execution_mode == "imported" else None
                run_evidence_audit(
                    SAMPLES[job.sample], self.job_dir(job.id), imported_result=imported,
                    recorded_at=IMPORTED_RECORDED_AT[job.sample] if imported else None,
                    job_id=job.id,
                    execute_reference_cut=True,
                    on_stage=self._stage_hook(job.id, events),
                    events=events,
                    recorded_events=IMPORTED_EVENTS.get(job.sample) if imported else None,
                )
        except AuditError as exc:
            logger.warning("Audit %s failed: %s", job.id, exc)
            self._fail(job, events, str(exc))
            return
        except Exception:  # noqa: BLE001 - the worker must never die silently
            logger.exception("Unexpected error in audit %s", job.id)
            self._fail(job, events, "Unexpected internal error; check the server logs.")
            return
        self.store.update(job.id, status="done", stage="done")

    def start_upload(self, filename: str, data: bytes, purpose: str = "audit") -> Job:
        """Uploads a repository as a ZIP. `audit`: live audit with Bob. `modernization`: only prepares it
        (no audit, no bobcoins) for the Modernization Studio, with any stack. Its code never runs."""
        if purpose == "modernization":
            job = self.store.create(f"modernize:{filename}", "live")
            self.executor.submit(self._execute_modernize_upload, job, data)
            return job
        with self._start_lock:
            if self.store.has_active("live"):
                raise BusyError("A live audit is already running; wait for it to finish.")
            job = self.store.create(f"upload:{filename}", "live")
        self.executor.submit(self._execute_upload, job, data)
        return job

    def _execute_modernize_upload(self, job: Job, data: bytes) -> None:
        self.store.update(job.id, status="running", stage="preparing")
        events = self.events(job.id)
        staging = self.job_dir(job.id) / "upload-src"
        try:
            events.emit("preparing", "stage.start", "pipeline", STAGE_LABELS["preparing"])
            validate_and_extract_zip(data, staging, max_files=MODERNIZE_MAX_FILES)
            _emit_zip_checks(events, data, max_files=MODERNIZE_MAX_FILES)
            self._keep_source(staging, job.id)
        except IngestionSecurityError as exc:
            logger.warning("Modernization upload %s rejected: %s", job.id, exc)
            self._fail(job, events, str(exc))
            return
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error preparing %s", job.id)
            self._fail(job, events, "Unexpected internal error; check the server logs.")
            return
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        events.emit("preparing", "inventory", "python", "Project prepared for modernization (no evidence audit)")
        self.store.update(job.id, status="done", stage="done")

    def _keep_source(self, staging: Path, job_id: str) -> Path:
        """Keeps a full copy (no dependencies, no .git) of the uploaded code: the Modernization Studio's base."""
        entries = list(staging.iterdir())
        repo = entries[0] if len(entries) == 1 and entries[0].is_dir() else staging
        target = self.job_dir(job_id) / "source"
        shutil.copytree(repo, target, ignore=COPY_IGNORE, dirs_exist_ok=True)
        return repo

    def modernize_adapter_factory(self, work: Path, kind: str):
        return default_adapter(work, kind)

    def _execute_upload(self, job: Job, data: bytes) -> None:
        self.store.update(job.id, status="running", stage="preparing")
        events = self.events(job.id)
        source = self.job_dir(job.id) / "upload-src"
        try:
            events.emit("preparing", "stage.start", "pipeline", STAGE_LABELS["preparing"])
            validate_and_extract_zip(data, source)
            _emit_zip_checks(events, data)
            # Many ZIP files carry a single root folder: that folder is the repository.
            repo = self._keep_source(source, job.id)
            run_evidence_audit(
                repo,
                self.job_dir(job.id),
                job_id=job.id,
                execute_reference_cut=False,
                on_stage=self._stage_hook(job.id, events),
                events=events,
                keep_tests=True,
            )
        except (AuditError, IngestionSecurityError) as exc:
            logger.warning("Audit %s failed: %s", job.id, exc)
            self._fail(job, events, str(exc))
            return
        except Exception:  # noqa: BLE001 - the worker must never die silently
            logger.exception("Unexpected error in audit %s", job.id)
            self._fail(job, events, "Unexpected internal error; check the server logs.")
            return
        finally:
            shutil.rmtree(source, ignore_errors=True)
        self.store.update(job.id, status="done", stage="done")

    def _materialize_example(self, job: Job) -> None:
        """Example mode: copies the example dossier and the code for the viewer."""
        target = self.job_dir(job.id)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SAMPLES[job.sample], target / "workspace",
                        ignore=shutil.ignore_patterns("*.sqlite3", "__pycache__"))
        shutil.copy2(EXAMPLE_DOSSIER, target / DOSSIER_FILE)

    def get_job(self, job_id: str) -> Job:
        job = self.store.get(job_id)
        if job is None:
            raise NotFoundError(f"Unknown job: {job_id}")
        return job

    def get_dossier(self, job_id: str) -> Dossier | None:
        job = self.get_job(job_id)
        path = self.job_dir(job_id) / DOSSIER_FILE
        # The worker writes dossier.json before marking the job done; reading it earlier
        # can hit a half-written file (or a locked one, on Windows).
        if job.status != "done" or not path.is_file():
            return None
        return Dossier.model_validate_json(path.read_text(encoding="utf-8"))

    def read_source(self, job_id: str, relative: str, start: int, end: int) -> SourceExcerpt:
        """Returns lines from the job's workspace; never leaves its root."""
        self.get_job(job_id)
        root = (self.job_dir(job_id) / "workspace").resolve()
        target = resolve_inside(root, relative)
        if target is None or not target.is_file() or ".bob" in target.relative_to(root).parts:
            raise NotFoundError(f"File not available: {relative}")
        if target.stat().st_size > MAX_SOURCE_BYTES:
            # A dump or bundle uploaded by mistake is never loaded whole into memory on every request.
            raise NotFoundError(f"The file is too large for the viewer (max {MAX_SOURCE_BYTES // 1_000_000} MB): {relative}")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(start, 1)
        end = min(max(end, start), len(lines), start + MAX_SOURCE_LINES - 1)
        return SourceExcerpt(
            path=relative, start=start, end=end, total_lines=len(lines),
            lines=[SourceLine(number=n, text=lines[n - 1]) for n in range(start, end + 1)],
        )


_BOB_VERSION_LOCK = threading.Lock()
_BOB_VERSIONS: dict[str, str] = {}


def _read_bob_version(binary: str) -> str | None:
    completed = subprocess.run(  # noqa: S603 - argument list, no shell
        [binary, "--version"], capture_output=True, text=True,
        timeout=BOB_VERSION_TIMEOUT_S, check=False,
    )
    output = completed.stdout.strip()
    return output.splitlines()[0] if output else None


def bob_version(binary: str) -> str | None:
    """Bob Shell version, computed once per process.

    The binary does not change while the container lives, and launching the CLI on every request cost
    ~15 s on Render (with the analysis button blocked) and one Node process per visit. A failure is not
    cached: the next request retries it.
    """
    with _BOB_VERSION_LOCK:  # concurrent requests wait for a single computation
        cached = _BOB_VERSIONS.get(binary)
        if cached:
            return cached
        try:
            version = _read_bob_version(binary)
        except (OSError, subprocess.TimeoutExpired):
            logger.warning("Could not read the Bob version", exc_info=True)
            return None
        if version:
            _BOB_VERSIONS[binary] = version
        return version


def warm_bob_version() -> None:
    """Computes the version at startup so no visit waits for the Bob CLI."""
    binary = shutil.which(BobRunSettings.from_env().bob_binary)
    if binary:
        bob_version(binary)


def bob_status() -> BobStatus:
    """Diagnostics of the Bob integration (spends no bobcoins)."""
    settings = BobRunSettings.from_env()
    binary = shutil.which(settings.bob_binary)
    bob_dir = CUSTOM_MODES_FILE.parent
    return BobStatus(
        installed=binary is not None,
        version=bob_version(binary) if binary else None,
        api_key_configured=bool(os.environ.get("BOB_API_KEY")),
        custom_modes=sorted(load_custom_mode_slugs()),
        subagents=sorted(p.stem for p in (bob_dir / "agents").glob("*.md")),
        skills=sorted(p.parent.name for p in (bob_dir / "skills").glob("*/SKILL.md")),
        max_cost_per_run=settings.max_cost,
        timeout_s=settings.timeout_s,
        live_requires_token=bool(os.environ.get("LIVE_AUDIT_TOKEN")),
    )
