"""Modernization Studio: detected stack, feasibility assessment, detailed plan and implementation with Bob.

- GET  /api/audits/{id}/modernization           : state (phase, assessment, plan, implementation, activity).
- GET  /api/audits/{id}/modernization/stack     : measured stack (languages, frameworks, data, infrastructure, architecture).
- POST /api/audits/{id}/modernization/assess    : Bob assesses whether migrating pays off and what is traded away (read-only).
- POST /api/audits/{id}/modernization/plan      : detailed plan by steps and dependencies.
- POST /api/audits/{id}/modernization/implement : Bob implements the plan on a copy; requires `confirm: true`.
- GET  /api/audits/{id}/modernization/download/{name} : ZIP of the migrated project, or the diff.

Operations that invoke Bob require the token only in locked mode (LIVE_AUDIT_TOKEN set). Uploaded code never runs.
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
        studio.source  # noqa: B018 - checks that the code is still available
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
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Implementing requires explicit confirmation.")
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not available.")
    return FileResponse(path, media_type=_MEDIA[name], filename=f"{job_id}-{name}")
