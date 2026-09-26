"""POST /api/audits/{job_id}/ask: pregunta contextual a IBM Bob sobre un análisis terminado.

Siempre exige `X-Live-Token` (cada pregunta gasta bobcoins, también en la vitrina pública)
y el mismo control de acceso que el resto de lecturas del job.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.access import require_job_access, require_upload_token
from app.jobs.assistant import AskAnswer, AskRequest, AssistantBusyError, AssistantError, ask_bob
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
        raise HTTPException(status.HTTP_409_CONFLICT, "El análisis aún no termina; pregunta cuando esté completo.")
    # Las auditorías tienen `workspace`; los proyectos subidos solo para modernizar, su copia íntegra `source`.
    workspace = next((d for d in (service.job_dir(job_id) / "workspace", service.job_dir(job_id) / "source") if d.is_dir()), None)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El código de este análisis no está disponible.")
    try:
        return ask_bob(workspace, body)
    except AssistantBusyError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    except AssistantError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
