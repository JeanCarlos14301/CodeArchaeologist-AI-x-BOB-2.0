"""Control de acceso para auditorías privadas.

Las muestras registradas son una vitrina pública. Los repositorios subidos por una
persona son privados y todas sus lecturas requieren el mismo ``X-Live-Token`` que
protege la carga.
"""

import hmac
import os

from fastapi import HTTPException, status

from app.jobs.store import Job


def token_is_valid(token: str | None) -> bool:
    """Compara el token sin filtrar por tiempo información sobre su contenido."""
    expected = os.environ.get("LIVE_AUDIT_TOKEN", "")
    return bool(expected and token and hmac.compare_digest(token.encode(), expected.encode()))


def require_upload_token(token: str | None) -> None:
    """Protege operaciones que crean una auditoría privada y consumen bobcoins."""
    if not os.environ.get("LIVE_AUDIT_TOKEN", ""):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El servidor no tiene LIVE_AUDIT_TOKEN configurado; no acepta auditorías.",
        )
    if not token_is_valid(token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token inválido.")


def is_private(job: Job) -> bool:
    """Solo los ZIP subidos por visitantes contienen código privado."""
    return job.sample.startswith(("upload:", "modernize:"))


def require_job_access(job: Job, token: str | None) -> None:
    """Exige token para cada lectura de un trabajo originado en un ZIP."""
    if is_private(job) and not token_is_valid(token):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esta auditoría privada requiere un X-Live-Token válido.",
        )
