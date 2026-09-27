"""POST /api/audits/{job_id}/ask: contextual question to IBM Bob about a finished analysis.

Requires `X-Live-Token` only in locked mode (each question spends bobcoins, also on the public
showcase) and applies the same access control as every other read of the job.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from pydantic import BaseModel

from app.api.access import require_job_access, require_upload_token
from app.jobs.assistant import (
    REQUEST_ID_PATTERN,
    AskAnswer,
    AskRequest,
    AskStep,
    AssistantBusyError,
    AssistantError,
    ask_bob,
    ask_progress,
)
from app.jobs.service import AuditService, NotFoundError

router = APIRouter(prefix="/api/audits", tags=["assistant"])


def get_service(request: Request) -> AuditService:
    return request.app.state.audit_service


Service = Annotated[AuditService, Depends(get_service)]


@router.post("/{job_id}/ask", response_model=AskAnswer)
def ask_about_audit(
    job_id: str,
    body: AskRequest,
    service: Service,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> AskAnswer:
    require_upload_token(x_live_token)
    try:
        job = service.get_job(job_id)
        require_job_access(job, x_live_token)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if job.status != "done":
        raise HTTPException(status.HTTP_409_CONFLICT, "The analysis has not finished yet; ask once it is complete.")
    # Audits have a `workspace`; projects uploaded only for modernization have their full copy in `source`.
    workspace = next((d for d in (service.job_dir(job_id) / "workspace", service.job_dir(job_id) / "source") if d.is_dir()), None)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The code for this analysis is not available.")
    try:
        return ask_bob(workspace, body)
    except AssistantBusyError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    except AssistantError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


class AskProgressPage(BaseModel):
    steps: list[AskStep]


@router.get("/{job_id}/ask/{request_id}/progress", response_model=AskProgressPage)
def ask_progress_page(
    job_id: str,
    service: Service,
    request_id: Annotated[str, Path(pattern=REQUEST_ID_PATTERN)],
    after: Annotated[int, Query(ge=0)] = 0,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> AskProgressPage:
    """What Bob is doing to answer a question (polled while it answers)."""
    require_upload_token(x_live_token)
    try:
        require_job_access(service.get_job(job_id), x_live_token)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return AskProgressPage(steps=ask_progress(request_id, after))
