"""Rutas HTTP de auditorías y diagnóstico de Bob. Los routers solo traducen HTTP ↔ servicio."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.access import require_job_access, require_upload_token, token_is_valid
from app.contracts.schema_v1 import Dossier
from app.jobs.service import (
    SAMPLES,
    AuditService,
    BobStatus,
    BusyError,
    NotFoundError,
    SourceExcerpt,
    bob_status,
)
from app.jobs.store import ExecutionMode, Job

router = APIRouter(prefix="/api")


class StartAuditRequest(BaseModel):
    sample: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    execution_mode: ExecutionMode = "live"


class AuditDetail(BaseModel):
    job: Job
    dossier: Dossier | None


class SampleInfo(BaseModel):
    id: str
    name: str


def get_service(request: Request) -> AuditService:
    return request.app.state.audit_service


def require_live_token(execution_mode: ExecutionMode, token: str | None) -> None:
    """Si LIVE_AUDIT_TOKEN está definido (despliegue público), live exige ese token.

    Sin la variable (desarrollo local) live queda abierto. imported y example nunca lo piden.
    """
    expected = os.environ.get("LIVE_AUDIT_TOKEN", "")
    if execution_mode != "live" or not expected:
        return
    if not token_is_valid(token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El modo live requiere un token válido.")


Service = Annotated[AuditService, Depends(get_service)]


@router.get("/bob/status", response_model=BobStatus)
def read_bob_status() -> BobStatus:
    return bob_status()


@router.get("/samples", response_model=list[SampleInfo])
def list_samples() -> list[SampleInfo]:
    return [SampleInfo(id=key, name=path.name) for key, path in SAMPLES.items()]


@router.post("/audits", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
def start_audit(
    body: StartAuditRequest,
    service: Service,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> Job:
    if body.execution_mode == "imported" and body.sample in SAMPLES:
        # Vitrina pública: reproduce una respuesta real ya grabada y no invoca Bob.
        pass
    elif os.environ.get("ALLOW_NON_LIVE_MODES", "").lower() == "true":
        require_live_token(body.execution_mode, x_live_token)
    else:
        # Por defecto solo hay auditorías reales: modo live y token siempre obligatorio.
        if body.execution_mode != "live":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo se permiten auditorías live (datos reales).")
        require_upload_token(x_live_token)
    try:
        return service.start(body.sample, body.execution_mode)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except BusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/audits", response_model=list[Job])
def list_audits(
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> list[Job]:
    jobs = service.store.list(limit)
    if token_is_valid(x_live_token):
        return jobs
    return service.store.list_public(limit)


@router.get("/audits/{job_id}", response_model=AuditDetail)
def read_audit(
    job_id: str,
    service: Service,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> AuditDetail:
    try:
        job = service.get_job(job_id)
        require_job_access(job, x_live_token)
        return AuditDetail(job=job, dossier=service.get_dossier(job_id))
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/audits/{job_id}/source", response_model=SourceExcerpt)
def read_source(
    job_id: str,
    service: Service,
    path: Annotated[str, Query(min_length=1, max_length=300)],
    start: Annotated[int, Query(ge=1)] = 1,
    end: Annotated[int, Query(ge=1)] = 400,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> SourceExcerpt:
    try:
        require_job_access(service.get_job(job_id), x_live_token)
        return service.read_source(job_id, path, start, end)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
