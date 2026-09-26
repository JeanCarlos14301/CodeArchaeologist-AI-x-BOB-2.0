"""Router de la API REST para Jobs de Auditoría Forense (D-02).

Endpoints:
- POST /api/jobs : Motor histórico de desarrollo para demo o archivo ZIP.
- GET  /api/jobs : Lista los jobs recientes y su estado.
- GET  /api/jobs/{id} : Retorna el estado, etapa actual (1 a 11), progreso porcentual y eventos.
- GET  /api/jobs/{id}/result : Retorna el expediente DossierResult conforme a schema-v1.json (409 si está procesando).
"""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from backend.app.database import (
    create_job,
    get_job,
    get_job_events,
    get_job_result,
    list_jobs,
)
from backend.app.models import (
    DossierResult,
    JobCreateRequest,
    JobProgressEvent,
    JobStatusResponse,
)
from backend.app.worker import launch_job_in_background

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_analysis_job(
    request: Optional[JobCreateRequest] = None,
    source_type: Optional[str] = Form(None),
    execution_mode: Optional[str] = Form(None),
    zip_file: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """Crea y encola un nuevo análisis de repositorio."""
    job_id = str(uuid.uuid4())

    effective_source_type = "demo"
    effective_mode = "example"
    zip_bytes = None

    if zip_file is not None:
        effective_source_type = "zip"
        effective_mode = execution_mode or "example"
        zip_bytes = await zip_file.read()
    elif source_type is not None:
        effective_source_type = source_type
        effective_mode = execution_mode or "example"
    elif request is not None:
        effective_source_type = request.source_type
        effective_mode = "example"

    if effective_source_type not in ["demo", "zip"]:
        raise HTTPException(
            status_code=400,
            detail=f"source_type no soportado: '{effective_source_type}'. Use 'demo' o 'zip'.",
        )

    # Registrar en base de datos SQLite
    create_job(
        job_id=job_id,
        source_type=effective_source_type,
        execution_mode=effective_mode,
    )

    # Iniciar worker en background
    launch_job_in_background(
        job_id=job_id,
        source_type=effective_source_type,
        zip_bytes_or_path=zip_bytes,
        requested_mode=effective_mode,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "source_type": effective_source_type,
        "execution_mode": effective_mode,
        "message": "Job de análisis creado y encolado exitosamente.",
    }


@router.get("", response_model=List[JobStatusResponse])
def get_recent_jobs() -> List[JobStatusResponse]:
    """Lista los análisis más recientes."""
    raw_jobs = list_jobs(limit=50)
    result = []
    for j in raw_jobs:
        raw_events = get_job_events(j["id"])
        events = [
            JobProgressEvent(
                stage=e["stage"],
                stage_name=e["stage_name"],
                status=e["status"],
                duration_ms=e["duration_ms"],
                timestamp=e["timestamp"],
                message=e["message"] or "",
            )
            for e in raw_events
        ]
        result.append(
            JobStatusResponse(
                job_id=j["id"],
                status=j["status"],
                stage=j["stage"],
                stage_name=j["stage_name"],
                progress_percent=j["progress_percent"],
                source_type=j["source_type"],
                execution_mode=j["execution_mode"],
                events=events,
                error_message=j.get("error_message"),
                created_at=j["created_at"],
                updated_at=j["updated_at"],
            )
        )
    return result


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    """Consulta el progreso y eventos de un job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")

    raw_events = get_job_events(job_id)
    events = [
        JobProgressEvent(
            stage=e["stage"],
            stage_name=e["stage_name"],
            status=e["status"],
            duration_ms=e["duration_ms"],
            timestamp=e["timestamp"],
            message=e["message"] or "",
        )
        for e in raw_events
    ]

    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        stage=job["stage"],
        stage_name=job["stage_name"],
        progress_percent=job["progress_percent"],
        source_type=job["source_type"],
        execution_mode=job["execution_mode"],
        events=events,
        error_message=job.get("error_message"),
        created_at=job["created_at"],
        updated_at=job["updated_at"],
    )


@router.get("/{job_id}/result", response_model=DossierResult)
def get_job_dossier_result(job_id: str) -> Any:
    """Obtiene el expediente DossierResult completo una vez terminado el análisis."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")

    if job["status"] in ["queued", "running"]:
        raise HTTPException(
            status_code=409,
            detail=f"El análisis aún está en procesamiento (etapa {job['stage']}: {job['stage_name']}, {job['progress_percent']}%).",
        )

    if job["status"] == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"El análisis falló: {job.get('error_message', 'Error desconocido')}",
        )

    result_json = get_job_result(job_id)
    if not result_json:
        raise HTTPException(status_code=404, detail="Resultado no disponible")

    return result_json
