"""Estudio de modernización: stack detectado, evaluación de viabilidad, plan detallado e implementación con Bob.

- GET  /api/audits/{id}/modernization           : estado (fase, evaluación, plan, implementación, actividad).
- GET  /api/audits/{id}/modernization/stack     : stack medido (lenguajes, frameworks, datos, infraestructura, arquitectura).
- POST /api/audits/{id}/modernization/assess    : Bob evalúa si conviene migrar y qué se sacrifica (solo lectura).
- POST /api/audits/{id}/modernization/plan      : plan detallado por pasos y dependencias.
- POST /api/audits/{id}/modernization/implement : Bob implementa el plan sobre una copia; exige `confirm: true`.
- GET  /api/audits/{id}/modernization/download/{name} : ZIP del proyecto migrado o diff.

Las operaciones que invocan a Bob exigen SIEMPRE el token. El código subido nunca se ejecuta.
"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.access import require_job_access, require_upload_token
from app.jobs.service import AuditService, NotFoundError
from app.modernization.models import AssessRequest, StudioState
from app.modernization.stack_scan import StackReport
from app.modernization.studio import Studio, StudioBusyError, StudioStateError

router = APIRouter(prefix="/api/audits/{job_id}/modernization", tags=["modernization"])

_MEDIA = {"modernized.zip": "application/zip", "migration.diff": "text/plain; charset=utf-8"}


def get_service(request: Request) -> AuditService:
    return request.app.state.audit_service


Service = Annotated[AuditService, Depends(get_service)]
Token = Annotated[str | None, Header(alias="X-Live-Token", max_length=200)]


class ImplementRequest(BaseModel):
    confirm: bool = False


def _studio(service: AuditService, job_id: str, token: str | None) -> Studio:
    try:
        job = service.get_job(job_id)
        require_job_access(job, token)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    name = job.sample.split(":", 1)[-1]
    studio = Studio(service.job_dir(job_id), project_name=name, adapter_factory=service.modernize_adapter_factory)
    try:
        studio.source  # noqa: B018 - comprueba que el código sigue disponible
    except StudioStateError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return studio


@router.get("", response_model=StudioState)
def read_state(job_id: str, service: Service, x_live_token: Token = None) -> StudioState:
    return _studio(service, job_id, x_live_token).state()


@router.get("/stack", response_model=StackReport)
def read_stack(job_id: str, service: Service, x_live_token: Token = None) -> StackReport:
    return _studio(service, job_id, x_live_token).stack()


def _launch(service: AuditService, action, job_id: str) -> None:
    service.executor.submit(action)


@router.post("/assess", response_model=StudioState, status_code=status.HTTP_202_ACCEPTED)
def assess(job_id: str, body: AssessRequest, service: Service, x_live_token: Token = None) -> StudioState:
    require_upload_token(x_live_token)
    studio = _studio(service, job_id, x_live_token)
    try:
        studio.begin_assess(body)
    except StudioBusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except StudioStateError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    _launch(service, studio.run_assess, job_id)
    return studio.state()


@router.post("/plan", response_model=StudioState, status_code=status.HTTP_202_ACCEPTED)
def plan(job_id: str, service: Service, x_live_token: Token = None) -> StudioState:
    require_upload_token(x_live_token)
    studio = _studio(service, job_id, x_live_token)
    try:
        studio.begin_plan()
    except StudioBusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except StudioStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    _launch(service, studio.run_plan, job_id)
    return studio.state()


@router.post("/implement", response_model=StudioState, status_code=status.HTTP_202_ACCEPTED)
def implement(job_id: str, body: ImplementRequest, service: Service, x_live_token: Token = None) -> StudioState:
    require_upload_token(x_live_token)
    if not body.confirm:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Implementar exige confirmar de forma explícita.")
    studio = _studio(service, job_id, x_live_token)
    try:
        studio.begin_implement()
    except StudioBusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except StudioStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    _launch(service, studio.run_implement, job_id)
    return studio.state()


@router.get("/download/{name}")
def download(job_id: str, name: str, service: Service, x_live_token: Token = None) -> FileResponse:
    studio = _studio(service, job_id, x_live_token)
    path: Path | None = studio.artifact(name)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no disponible.")
    return FileResponse(path, media_type=_MEDIA[name], filename=f"{job_id}-{name}")
