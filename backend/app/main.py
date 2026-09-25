"""Punto de entrada principal de FastAPI para LegacyLens (D-02, D11).

Integra:
- Motor determinista de 11 etapas (/api/jobs, /api/jobs/{id}/migrate, /api/jobs/{id}/artifacts).
- API de auditorías y visor de fuentes para el frontend (/api/audits, /api/bob/status, /api/samples).
- Configuración de CORS para desarrollo local y producción.
- Inicialización de bases de datos y servicios en el ciclo de vida (lifespan).
- Servidor de archivos estáticos para la SPA de React (frontend/dist).
"""

from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.adapters.bob_adapter import (
    REPO_ROOT,
    determine_operational_mode,
    get_bob_api_key,
    is_bob_cli_available,
)
from backend.app.api.artifacts import router as artifacts_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.migrate import router as migrate_router
from backend.app.api.routes import router as felipe_routes_router
from backend.app.database import init_db
from backend.app.jobs.service import AuditService
from backend.app.jobs.store import JobStore

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"))
DEV_ORIGINS = ["*", "http://localhost:5173", "http://127.0.0.1:5173"]


def _load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Carga .env sin pisar variables ya definidas."""
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
    """Fábrica de aplicación FastAPI que inicializa ambos subsistemas."""
    _load_dotenv()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Inicializar base de datos determinista SQLite con WAL
        init_db()

        # Inicializar JobStore y AuditService para el frontend
        jobs_dir = artifacts_dir / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        store = JobStore(artifacts_dir / "jobs.db")
        store.fail_orphans()
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit")
        app.state.audit_service = AuditService(store, jobs_dir, executor)

        yield

        executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title="LegacyLens — Forensic Legacy Migration API",
        description="Motor determinista de diagnóstico forense de repositorios, evaluación de radio de explosión y migración Strangler Fig con IBM Bob Shell 2.0.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registro de routers de API de Daniel
    app.include_router(jobs_router)
    app.include_router(migrate_router)
    app.include_router(artifacts_router)

    # Registro de router de auditorías de Felipe / Frontend
    app.include_router(felipe_routes_router)

    @app.get("/health", tags=["health"])
    def health_check() -> Dict[str, Any]:
        """Endpoint de verificación de estado y disponibilidad de Bob Shell."""
        cli_found = is_bob_cli_available()
        api_key_set = bool(get_bob_api_key())
        mode = determine_operational_mode()

        return {
            "status": "ok",
            "service": "LegacyLens Core Backend",
            "version": "1.0.0",
            "bob_shell_available": cli_found,
            "bob_api_key_configured": api_key_set,
            "execution_mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Servir archivos estáticos del frontend React/Vite
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
