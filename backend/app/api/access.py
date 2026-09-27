"""Access control for audits and Bob calls.

``LIVE_AUDIT_TOKEN`` is optional:

- **Unset (open mode):** anyone can start a live audit, ask Bob or use the Studio. Spending is
  bounded by the per-run bobcoin caps, the one-audit-at-a-time rule and the Bob account budget.
  Uploaded repositories are never listed publicly; they are reachable only through their job id.
- **Set (locked mode):** every operation that calls Bob, and every read of an uploaded repository,
  requires the same ``X-Live-Token``. Setting the variable is the kill switch if the public URL is
  abused.

The recorded samples are a public showcase in both modes.
"""

import hmac
import os

from fastapi import HTTPException, status

from app.jobs.store import Job


def token_configured() -> bool:
    """True when the server is in locked mode."""
    return bool(os.environ.get("LIVE_AUDIT_TOKEN", ""))


def token_is_valid(token: str | None) -> bool:
    """Constant-time comparison, so response timing leaks nothing about the token."""
    expected = os.environ.get("LIVE_AUDIT_TOKEN", "")
    return bool(expected and token and hmac.compare_digest(token.encode(), expected.encode()))


def require_upload_token(token: str | None) -> None:
    """Guards operations that call Bob and spend bobcoins; open when no token is configured."""
    if token_configured() and not token_is_valid(token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid access token.")


def is_private(job: Job) -> bool:
    """Only ZIP files uploaded by visitors contain private code."""
    return job.sample.startswith(("upload:", "modernize:"))


def require_job_access(job: Job, token: str | None) -> None:
    """In locked mode, every read of a job created from a ZIP requires the token."""
    if token_configured() and is_private(job) and not token_is_valid(token):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This private audit requires a valid X-Live-Token.",
        )
