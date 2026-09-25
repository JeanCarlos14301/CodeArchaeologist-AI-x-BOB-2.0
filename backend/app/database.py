"""Persistencia SQLite local para jobs y eventos del pipeline determinista (D-02).

Habilita WAL mode para concurrencia segura y rendimiento.
Almacena el estado del job, eventos de cada una de las 11 etapas y el resultado final DossierResult.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BASE_DIR / "jobs.db"


def get_db_path() -> Path:
    env_path = os.environ.get("DATABASE_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Inicializa el esquema de base de datos si no existe."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                stage INTEGER NOT NULL DEFAULT 0,
                stage_name TEXT NOT NULL DEFAULT 'Iniciado',
                progress_percent INTEGER NOT NULL DEFAULT 0,
                source_type TEXT NOT NULL,
                source_path TEXT,
                execution_mode TEXT NOT NULL DEFAULT 'example',
                result_json TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                stage INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_events_job_id ON job_events(job_id);
        """)
    conn.close()


def create_job(
    job_id: str,
    source_type: str,
    source_path: Optional[str] = None,
    execution_mode: str = "example",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Registra un nuevo job en cola."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, status, stage, stage_name, progress_percent,
                source_type, source_path, execution_mode,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                "queued",
                0,
                "En cola",
                0,
                source_type,
                source_path,
                execution_mode,
                now,
                now,
            ),
        )
    conn.close()
    return get_job(job_id, db_path=db_path)  # type: ignore


def update_job_status(
    job_id: str,
    status: str,
    stage: int,
    stage_name: str,
    progress_percent: int,
    error_message: Optional[str] = None,
    execution_mode: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Actualiza el progreso y estado de un job."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    with conn:
        if execution_mode:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, stage = ?, stage_name = ?, progress_percent = ?,
                    error_message = ?, execution_mode = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, stage, stage_name, progress_percent, error_message, execution_mode, now, job_id),
            )
        else:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, stage = ?, stage_name = ?, progress_percent = ?,
                    error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, stage, stage_name, progress_percent, error_message, now, job_id),
            )
    conn.close()


def save_job_result(
    job_id: str,
    result_dict: Dict[str, Any],
    db_path: Optional[Path] = None,
) -> None:
    """Guarda el expediente JSON final de un job completado."""
    now = datetime.now(timezone.utc).isoformat()
    json_str = json.dumps(result_dict, ensure_ascii=False)
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            UPDATE jobs
            SET result_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (json_str, now, job_id),
        )
    conn.close()


def add_job_event(
    job_id: str,
    stage: int,
    stage_name: str,
    status: str,
    duration_ms: int = 0,
    message: str = "",
    db_path: Optional[Path] = None,
) -> None:
    """Registra un evento de etapa en la línea de tiempo del job."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO job_events (
                job_id, stage, stage_name, status, duration_ms, message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, stage, stage_name, status, duration_ms, message, now),
        )
    conn.close()


def get_job(job_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Obtiene los detalles del job por ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def get_job_events(job_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Obtiene los eventos cronológicos de un job."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM job_events WHERE job_id = ? ORDER BY id ASC",
        (job_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job_result(job_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Obtiene el resultado JSON parseado de un job."""
    job = get_job(job_id, db_path=db_path)
    if not job or not job.get("result_json"):
        return None
    return json.loads(job["result_json"])


def list_jobs(limit: int = 50, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Lista los jobs recientes."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
