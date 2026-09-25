"""Rutas HTTP de auditorías y diagnóstico de Bob. Los routers solo traducen HTTP ↔ servicio."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

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


Service = Annotated[AuditService, Depends(get_service)]


@router.get("/bob/status", response_model=BobStatus)
def read_bob_status() -> BobStatus:
    return bob_status()


@router.get("/samples", response_model=list[SampleInfo])
def list_samples() -> list[SampleInfo]:
    return [SampleInfo(id=key, name=path.name) for key, path in SAMPLES.items()]


@router.post("/audits", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
def start_audit(body: StartAuditRequest, service: Service) -> Job:
    try:
        return service.start(body.sample, body.execution_mode)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except BusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/audits", response_model=list[Job])
def list_audits(service: Service, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[Job]:
    return service.store.list(limit)


@router.get("/audits/{job_id}", response_model=AuditDetail)
def read_audit(job_id: str, service: Service) -> AuditDetail:
    try:
        return AuditDetail(job=service.get_job(job_id), dossier=service.get_dossier(job_id))
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/audits/{job_id}/source", response_model=SourceExcerpt)
def read_source(
    job_id: str,
    service: Service,
    path: Annotated[str, Query(min_length=1, max_length=300)],
    start: Annotated[int, Query(ge=1)] = 1,
    end: Annotated[int, Query(ge=1)] = 400,
) -> SourceExcerpt:
    try:
        return service.read_source(job_id, path, start, end)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
