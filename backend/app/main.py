"""Punto de entrada de FastAPI: API + worker del pipeline + build estático del frontend (D11).

Desarrollo:  cd backend && uvicorn app.main:app --reload
"""

import logging
import os
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.adapters.bob_adapter import REPO_ROOT
from app.api.routes import router
from app.jobs.service import AuditService
from app.jobs.store import JobStore

ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"))
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def _load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Carga .env sin dependencias extra; nunca pisa variables ya definidas."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def create_app(artifacts_dir: Path = ARTIFACTS_DIR, frontend_dist: Path = FRONTEND_DIST) -> FastAPI:
    _load_dotenv()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = JobStore(artifacts_dir / "jobs.db")
        store.fail_orphans()
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit")
        app.state.audit_service = AuditService(store, artifacts_dir / "jobs", executor)
        yield
        executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(title="CodeArchaeologist", version="0.1.0", lifespan=lifespan)

    if os.environ.get("ENABLE_DEV_CORS", "true").lower() == "true":
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["GET", "POST"],
                           allow_headers=["Content-Type"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)

    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
