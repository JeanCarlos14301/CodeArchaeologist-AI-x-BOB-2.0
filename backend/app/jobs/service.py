"""Servicio de auditorías: lanza el pipeline en un worker y expone resultados y código fuente.

Solo se auditan muestras registradas (sin rutas arbitrarias del cliente) y solo puede
haber una auditoría `live` a la vez para acotar el gasto de bobcoins.
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
from app.pipeline.ingestion import (
    MAX_FILES_COUNT,
    MAX_UNCOMPRESSED_BYTES,
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
# Vitrina: sesión real de Bob grabada con stream-json (resultado + actividad de la misma sesión).
# `bob-evidence-auditor-facturaya.json` (sesión del 25-09, sin actividad) se conserva para la evaluación.
IMPORTED_FIXTURES: dict[str, Path] = {
    "facturaya-v1": FIXTURES_DIR / "bob-session-facturaya.json",
}
# Actividad real grabada de la misma sesión de Bob (stream-json saneado), para reproducirla.
IMPORTED_EVENTS: dict[str, Path] = {
    "facturaya-v1": FIXTURES_DIR / "bob-events-facturaya.jsonl",
}
# Proveniencia de la grabación versionada. Corresponde a la sesión documentada
# en docs/bob-usage.md; no se sustituye por la hora en que un visitante la abre.
IMPORTED_RECORDED_AT: dict[str, str] = {
    "facturaya-v1": "2026-09-26T00:27:50-05:00",
}
EXAMPLE_DOSSIER = FIXTURES_DIR / "dossier-example.json"
MAX_SOURCE_LINES = 400
BOB_VERSION_TIMEOUT_S = 15


STAGE_LABELS: dict[str, str] = {
    "preparing": "Indexando repositorio",
    "auditing": "Bob analiza el código",
    "validating": "Verificando evidencia",
    "migration": "Probando primer corte",
    "done": "Expediente listo",
}


def _emit_zip_checks(events: EventLog, data: bytes) -> None:
    """Controles de seguridad que el ZIP acaba de superar (todos ya validados en ingestion.py)."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
    uncompressed = sum(member.file_size for member in members)
    checks = [
        ("Tamaño comprimido", f"{len(data) / 1024:.0f} KB", f"≤ {MAX_ZIP_COMPRESSED_BYTES // (1024 * 1024)} MB"),
        ("Entradas en el ZIP", str(len(members)), f"≤ {MAX_FILES_COUNT}"),
        ("Tamaño descomprimido", f"{uncompressed / 1024:.0f} KB", f"≤ {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB (anti zip-bomb)"),
        ("Rutas", "sin «..» ni absolutas", "anti ZipSlip"),
        ("Enlaces simbólicos", "ninguno", "rechazados"),
        ("Binarios ejecutables", "ninguno", "rechazados"),
    ]
    for name, value, limit in checks:
        events.emit("preparing", "ingest.check", "python", name, None, {"value": value, "limit": limit, "status": "passed"})


class BusyError(RuntimeError):
    """Ya hay una auditoría live en curso."""


class NotFoundError(LookupError):
    """Recurso inexistente (job, muestra o archivo)."""


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

    def job_dir(self, job_id: str) -> Path:
        return self.artifacts_dir / job_id

    def start(self, sample: str, execution_mode: ExecutionMode) -> Job:
        if sample not in SAMPLES:
            raise NotFoundError(f"Muestra desconocida: {sample}")
        with self._start_lock:  # comprobar y crear de forma atómica: nunca dos auditorías live a la vez
            if execution_mode == "live" and self.store.has_active("live"):
                raise BusyError("Ya hay una auditoría live en curso; espera a que termine.")
            job = self.store.create(sample, execution_mode)
        self.executor.submit(self._execute, job)
        return job

    def events(self, job_id: str) -> EventLog:
        return EventLog(self.job_dir(job_id) / EVENTS_FILE)

    def _stage_hook(self, job_id: str, events: EventLog) -> Callable[[str], None]:
        def on_stage(stage: str) -> None:
            self.store.update(job_id, stage=stage)
            events.emit(stage, "stage.start", "pipeline", STAGE_LABELS.get(stage, stage))  # type: ignore[arg-type]
        return on_stage

    def _fail(self, job: Job, events: EventLog, message: str) -> None:
        """Marca el fallo conservando la etapa en la que ocurrió (la UI la señala con ✗).

        El mensaje se publica (feed y job): nunca lleva rutas del servidor.
        """
        message = redact_paths(message)
        stage = (self.store.get(job.id) or job).stage
        events.emit(stage if stage in STAGE_LABELS else "preparing", "pipeline.failed", "pipeline",  # type: ignore[arg-type]
                    "El análisis se detuvo", message)
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
            logger.warning("Auditoría %s falló: %s", job.id, exc)
            self._fail(job, events, str(exc))
            return
        except Exception:  # noqa: BLE001 - el worker nunca debe morir en silencio
            logger.exception("Error inesperado en la auditoría %s", job.id)
            self._fail(job, events, "Error interno inesperado; revisa los logs del servidor.")
            return
        self.store.update(job.id, status="done", stage="done")

    def start_upload(self, filename: str, data: bytes) -> Job:
        """Audita en vivo (Bob real) un repositorio subido como ZIP. Nunca ejecuta su código."""
        with self._start_lock:
            if self.store.has_active("live"):
                raise BusyError("Ya hay una auditoría live en curso; espera a que termine.")
            job = self.store.create(f"upload:{filename}", "live")
        self.executor.submit(self._execute_upload, job, data)
        return job

    def _execute_upload(self, job: Job, data: bytes) -> None:
        self.store.update(job.id, status="running", stage="preparing")
        events = self.events(job.id)
        source = self.job_dir(job.id) / "upload-src"
        try:
            events.emit("preparing", "stage.start", "pipeline", STAGE_LABELS["preparing"])
            validate_and_extract_zip(data, source)
            _emit_zip_checks(events, data)
            entries = list(source.iterdir())
            # Muchos ZIP traen una única carpeta raíz: el repositorio es esa carpeta.
            repo = entries[0] if len(entries) == 1 and entries[0].is_dir() else source
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
            logger.warning("Auditoría %s falló: %s", job.id, exc)
            self._fail(job, events, str(exc))
            return
        except Exception:  # noqa: BLE001 - el worker nunca debe morir en silencio
            logger.exception("Error inesperado en la auditoría %s", job.id)
            self._fail(job, events, "Error interno inesperado; revisa los logs del servidor.")
            return
        finally:
            shutil.rmtree(source, ignore_errors=True)
        self.store.update(job.id, status="done", stage="done")

    def _materialize_example(self, job: Job) -> None:
        """Modo example: copia el expediente de ejemplo y el código para el visor."""
        target = self.job_dir(job.id)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SAMPLES[job.sample], target / "workspace",
                        ignore=shutil.ignore_patterns("*.sqlite3", "__pycache__"))
        shutil.copy2(EXAMPLE_DOSSIER, target / DOSSIER_FILE)

    def get_job(self, job_id: str) -> Job:
        job = self.store.get(job_id)
        if job is None:
            raise NotFoundError(f"Job inexistente: {job_id}")
        return job

    def get_dossier(self, job_id: str) -> Dossier | None:
        job = self.get_job(job_id)
        path = self.job_dir(job_id) / DOSSIER_FILE
        # El worker escribe dossier.json antes de marcar el job como done; leerlo antes
        # puede toparse con el archivo a medio escribir (o bloqueado, en Windows).
        if job.status != "done" or not path.is_file():
            return None
        return Dossier.model_validate_json(path.read_text(encoding="utf-8"))

    def read_source(self, job_id: str, relative: str, start: int, end: int) -> SourceExcerpt:
        """Devuelve líneas del workspace del job; nunca sale de su raíz."""
        self.get_job(job_id)
        root = (self.job_dir(job_id) / "workspace").resolve()
        target = resolve_inside(root, relative)
        if target is None or not target.is_file() or ".bob" in target.relative_to(root).parts:
            raise NotFoundError(f"Archivo no disponible: {relative}")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(start, 1)
        end = min(max(end, start), len(lines), start + MAX_SOURCE_LINES - 1)
        return SourceExcerpt(
            path=relative, start=start, end=end, total_lines=len(lines),
            lines=[SourceLine(number=n, text=lines[n - 1]) for n in range(start, end + 1)],
        )


def bob_status() -> BobStatus:
    """Diagnóstico de la integración con Bob (sin gastar bobcoins)."""
    settings = BobRunSettings.from_env()
    binary = shutil.which(settings.bob_binary)
    version = None
    if binary:
        try:
            completed = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
                [binary, "--version"], capture_output=True, text=True,
                timeout=BOB_VERSION_TIMEOUT_S, check=False,
            )
            version = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else None
        except (OSError, subprocess.TimeoutExpired):
            logger.warning("No se pudo obtener la versión de Bob", exc_info=True)
    bob_dir = CUSTOM_MODES_FILE.parent
    return BobStatus(
        installed=binary is not None,
        version=version,
        api_key_configured=bool(os.environ.get("BOB_API_KEY")),
        custom_modes=sorted(load_custom_mode_slugs()),
        subagents=sorted(p.stem for p in (bob_dir / "agents").glob("*.md")),
        skills=sorted(p.parent.name for p in (bob_dir / "skills").glob("*/SKILL.md")),
        max_cost_per_run=settings.max_cost,
        timeout_s=settings.timeout_s,
        live_requires_token=bool(os.environ.get("LIVE_AUDIT_TOKEN")),
    )
