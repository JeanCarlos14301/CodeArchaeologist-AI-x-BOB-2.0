"""Punto de entrada principal de FastAPI para CodeArchaeologist (D-02, D11).

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
import threading
from typing import Any, Dict

from fastapi import FastAPI
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
    from app.api.routes import router as felipe_routes_router
    from app.database import init_db
    from app.jobs.service import AuditService, warm_bob_version
    from app.jobs.store import JobStore
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
    from backend.app.api.routes import router as felipe_routes_router
    from backend.app.database import init_db
    from backend.app.jobs.service import AuditService, warm_bob_version
    from backend.app.jobs.store import JobStore

if "app" in sys.modules and "backend.app" not in sys.modules:
    sys.modules["backend.app"] = sys.modules["app"]
elif "backend.app" in sys.modules and "app" not in sys.modules:
    sys.modules["app"] = sys.modules["backend.app"]

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", REPO_ROOT / "artifacts"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"))
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


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
        # En segundo plano: el CLI de Bob tarda ~15 s en arrancar en Render y el arranque no lo espera.
        threading.Thread(target=warm_bob_version, name="bob-version", daemon=True).start()

        yield

        stopped = terminate_active_sessions()
        if stopped:
            logger.warning("Se terminaron %s sesiones de Bob en curso al apagar el servidor", stopped)
        executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title="CodeArchaeologist — Forensic Legacy Migration API",
        description="Motor determinista de diagnóstico forense de repositorios, evaluación de radio de explosión y migración Strangler Fig con IBM Bob Shell 2.0.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS solo para el servidor de desarrollo de Vite; en producción el frontend se sirve
    # desde el mismo origen (Dockerfile fija ENABLE_DEV_CORS=false).
    if os.environ.get("ENABLE_DEV_CORS", "true").lower() == "true":
        app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["GET", "POST"],
                           allow_headers=["Content-Type", "X-Live-Token"])

    # Registro de routers principales de auditorías y diagnóstico
    app.include_router(live_router)
    app.include_router(assistant_router)
    app.include_router(activity_router)
    app.include_router(felipe_routes_router)

    @app.get("/health", tags=["health"])
    def health_check() -> Dict[str, Any]:
        """Endpoint de verificación de estado y disponibilidad de Bob Shell."""
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

    # Servir archivos estáticos del frontend React/Vite
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
