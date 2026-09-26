"""GET /api/audits/{job_id}/events: actividad de cada etapa del análisis, paginada por cursor.

El frontend la sondea mientras el análisis corre (`after` = último `seq` recibido) y la reproduce
cuando ya terminó. Mismo control de acceso que el resto de lecturas del job.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.access import require_job_access
from app.jobs.service import AuditService, NotFoundError
from app.pipeline.activity import EVENTS_FILE, MAX_EVENTS_PER_PAGE, PipelineEvent, read_events

router = APIRouter(prefix="/api/audits", tags=["activity"])


class ActivityPage(BaseModel):
    job_id: str
    job_status: str
    events: list[PipelineEvent]
    next_after: int
    has_more: bool


def get_service(request: Request) -> AuditService:
    return request.app.state.audit_service


Service = Annotated[AuditService, Depends(get_service)]


@router.get("/{job_id}/events", response_model=ActivityPage)
def read_activity(
    job_id: str,
    service: Service,
    after: Annotated[int, Query(ge=0)] = 0,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> ActivityPage:
    try:
        job = service.get_job(job_id)
        require_job_access(job, x_live_token)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    events = read_events(service.job_dir(job_id) / EVENTS_FILE, after=after)
    return ActivityPage(
        job_id=job_id,
        job_status=job.status,
        events=events,
        next_after=events[-1].seq if events else after,
        has_more=len(events) >= MAX_EVENTS_PER_PAGE,
    )
