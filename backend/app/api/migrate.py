"""Router para la Ejecución del Primer Corte de Migración Strangler Fig (D-07).

Endpoint:
- POST /api/jobs/{id}/migrate : Ejecuta o actualiza la modernización del endpoint seleccionado y genera el diff.
"""

from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from backend.app.database import get_job, get_job_result, save_job_result
from backend.app.models import MigrateRequest, MigrationSummary
from backend.app.sandbox.migration_runner import apply_strangler_cut

router = APIRouter(prefix="/api/jobs", tags=["migration"])
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


@router.post("/{job_id}/migrate")
def trigger_migration_cut(job_id: str, request: MigrateRequest) -> Dict[str, Any]:
    """Aplica el corte Strangler Fig en el sandbox del job especificado."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")

    sandbox_repo = BASE_DIR / "sandboxes" / job_id / "repo"
    if not sandbox_repo.exists():
        # Si no existe sandbox directo, usar el directorio de muestras
        sandbox_repo = BASE_DIR / "samples" / "facturaya-v1"

    summary = apply_strangler_cut(sandbox_repo, endpoint=request.endpoint)

    # Actualizar resultado en base de datos si ya existía
    existing_result = get_job_result(job_id)
    if existing_result:
        existing_result["migration_summary"] = summary.model_dump()
        save_job_result(job_id, existing_result)

    return {
        "job_id": job_id,
        "endpoint": request.endpoint,
        "status": "applied",
        "migration_summary": summary.model_dump(),
    }
