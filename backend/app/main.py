"""Main FastAPI entry point for CodeArchaeologist (D-02, D11).

Wires together:
- The audits API and source viewer for the frontend (/api/audits, /api/bob/status, /api/samples).
- The Modernization Studio, the Ask Bob assistant and the activity feed.
- CORS for local development only.
- Database and service initialization in the lifespan.
- The static file server for the React SPA (frontend/dist).
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import threading
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
# The backend mixes `app.*` imports (rooted at backend/) and `backend.app.*` imports (rooted at
# the repo root), so both roots must be importable however uvicorn is launched
# (`uvicorn` script, `python -m uvicorn`, from the repo root or from backend/).
for _import_root in (str(REPO_ROOT / "backend"), str(REPO_ROOT)):
    if _import_root not in sys.path:
        sys.path.insert(0, _import_root)

try:
    from app.adapters.bob_adapter import (
        REPO_ROOT,
        determine_operational_mode,
        get_bob_api_key,
        is_bob_cli_available,
        terminate_active_sessions,
    )
    from app.api.activity import router as activity_router
    from app.api.assistant import router as assistant_router
    from app.api.live import router as live_router
    from app.api.modernization import router as modernization_router
    from app.api.routes import router as felipe_routes_router
    from app.database import init_db
    from app.jobs.service import AuditService, warm_bob_version
    from app.jobs.store import JobStore
    from app.modernization.studio import recover_interrupted
except ImportError:
    from backend.app.adapters.bob_adapter import (
        REPO_ROOT,
        determine_operational_mode,
        get_bob_api_key,
        is_bob_cli_available,
        terminate_active_sessions,
    )
    from backend.app.api.activity import router as activity_router
    from backend.app.api.assistant import router as assistant_router
    from backend.app.api.live import router as live_router
    from backend.app.api.modernization import router as modernization_router
    from backend.app.api.routes import router as felipe_routes_router
    from backend.app.database import init_db
    from backend.app.jobs.service import AuditService, warm_bob_version
    from backend.app.jobs.store import JobStore
    from backend.app.modernization.studio import recover_interrupted

if "app" in sys.modules and "backend.app" not in sys.modules:
    sys.modules["backend.app"] = sys.modules["app"]
elif "backend.app" in sys.modules and "app" not in sys.modules:
    sys.modules["app"] = sys.modules["backend.app"]

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"))
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


# Headers on every response (API and SPA). style-src allows inline styles: React sets `style` and the
# console SVGs carry their <style>; scripts only come from our own origin (the Vite build has no inline scripts).
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
        "font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=31536000",
}


def _load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Loads .env without overriding variables that are already set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def create_app(
    artifacts_dir: Path = ARTIFACTS_DIR,
    frontend_dist: Path = FRONTEND_DIST,
) -> FastAPI:
    """FastAPI application factory that initializes both subsystems."""
    _load_dotenv()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Initialize the deterministic SQLite database with WAL
        init_db()

        # Initialize the JobStore and the AuditService for the frontend
        jobs_dir = artifacts_dir / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        store = JobStore(artifacts_dir / "jobs.db")
        store.fail_orphans()
        recover_interrupted(jobs_dir)  # the Studio is never stuck in "assessing" after a restart
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit")
        app.state.audit_service = AuditService(store, jobs_dir, executor)
        # In the background: the Bob CLI takes ~15 s to start on Render and startup does not wait for it.
        threading.Thread(target=warm_bob_version, name="bob-version", daemon=True).start()

        yield

        stopped = terminate_active_sessions()
        if stopped:
            logger.warning("Terminated %s running Bob sessions while shutting down the server", stopped)
        executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title="CodeArchaeologist — Forensic Legacy Migration API",
        description="Forensic diagnosis of legacy repositories with IBM Bob Shell 2.0: verified evidence, blast radius and a Strangler Fig migration plan.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS only for the Vite dev server; in production the frontend is served from the
    # same origin (the Dockerfile sets ENABLE_DEV_CORS=false).
    if os.environ.get("ENABLE_DEV_CORS", "true").lower() == "true":
        app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["GET", "POST"],
                           allow_headers=["Content-Type", "X-Live-Token"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    # Register the main audit and diagnostics routers
    app.include_router(live_router)
    app.include_router(modernization_router)
    app.include_router(assistant_router)
    app.include_router(activity_router)
    app.include_router(felipe_routes_router)

    @app.get("/health", tags=["health"])
    def health_check() -> Dict[str, Any]:
        """Health check and Bob Shell availability."""
        cli_found = is_bob_cli_available()
        api_key_set = bool(get_bob_api_key())
        mode = determine_operational_mode()

        return {
            "status": "ok",
            "service": "CodeArchaeologist Core Backend",
            "version": "1.0.0",
            "bob_shell_available": cli_found,
            "bob_api_key_configured": api_key_set,
            "execution_mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Serve the React/Vite frontend's static files
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
