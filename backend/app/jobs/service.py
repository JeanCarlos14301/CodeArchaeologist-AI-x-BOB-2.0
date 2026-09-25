"""Servicio de auditorías: lanza el pipeline en un worker y expone resultados y código fuente.

Solo se auditan muestras registradas (sin rutas arbitrarias del cliente) y solo puede
haber una auditoría `live` a la vez para acotar el gasto de bobcoins.
"""

import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel

from app.adapters.bob_adapter import CUSTOM_MODES_FILE, REPO_ROOT, BobRunSettings, load_custom_mode_slugs
from app.contracts.schema_v1 import Dossier
from app.jobs.store import ExecutionMode, Job, JobStore
from app.pipeline.evidence_audit import DOSSIER_FILE, AuditError, run_evidence_audit
from app.validators.evidence import resolve_inside

logger = logging.getLogger(__name__)

SAMPLES: dict[str, Path] = {
    "facturaya-v1": REPO_ROOT / "samples" / "facturaya-v1" / "samples" / "facturaya-v1",
}
FIXTURES_DIR = REPO_ROOT / "contracts" / "fixtures"
IMPORTED_FIXTURES: dict[str, Path] = {
    "facturaya-v1": FIXTURES_DIR / "bob-evidence-auditor-facturaya.json",
}
EXAMPLE_DOSSIER = FIXTURES_DIR / "dossier-example.json"
MAX_SOURCE_LINES = 400
BOB_VERSION_TIMEOUT_S = 15


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


class AuditService:
    def __init__(self, store: JobStore, artifacts_dir: Path, executor: ThreadPoolExecutor) -> None:
        self.store = store
        self.artifacts_dir = artifacts_dir
        self.executor = executor

    def job_dir(self, job_id: str) -> Path:
        return self.artifacts_dir / job_id

    def start(self, sample: str, execution_mode: ExecutionMode) -> Job:
        if sample not in SAMPLES:
            raise NotFoundError(f"Muestra desconocida: {sample}")
        if execution_mode == "live" and self.store.has_active("live"):
            raise BusyError("Ya hay una auditoría live en curso; espera a que termine.")
        job = self.store.create(sample, execution_mode)
        self.executor.submit(self._execute, job)
        return job

    def _execute(self, job: Job) -> None:
        self.store.update(job.id, status="running", stage="preparing")
        try:
            if job.execution_mode == "example":
                self._materialize_example(job)
            else:
                imported = IMPORTED_FIXTURES[job.sample] if job.execution_mode == "imported" else None
                run_evidence_audit(
                    SAMPLES[job.sample], self.job_dir(job.id), imported_result=imported,
                    on_stage=lambda stage: self.store.update(job.id, stage=stage),
                )
        except AuditError as exc:
            logger.warning("Auditoría %s falló: %s", job.id, exc)
            self.store.update(job.id, status="failed", stage="failed", error=str(exc))
            return
        except Exception:  # noqa: BLE001 - el worker nunca debe morir en silencio
            logger.exception("Error inesperado en la auditoría %s", job.id)
            self.store.update(job.id, status="failed", stage="failed",
                              error="Error interno inesperado; revisa los logs del servidor.")
            return
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
        self.get_job(job_id)
        path = self.job_dir(job_id) / DOSSIER_FILE
        if not path.is_file():
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
    )
