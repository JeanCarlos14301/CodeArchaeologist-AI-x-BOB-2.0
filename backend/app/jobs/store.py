"""Almacén de jobs en SQLite (D-02). Una fila por auditoría; el expediente vive en disco."""

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

JobStatus = Literal["queued", "running", "done", "failed"]
ExecutionMode = Literal["live", "imported", "example"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    sample TEXT NOT NULL,
    execution_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


class Job(BaseModel):
    id: str
    sample: str
    execution_mode: ExecutionMode
    status: JobStatus
    stage: str
    error: str | None = None
    created_at: str
    updated_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    """Acceso a la tabla jobs con consultas parametrizadas; seguro entre hilos."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._connection.execute(_SCHEMA)
            self._connection.commit()

    def create(self, sample: str, execution_mode: ExecutionMode) -> Job:
        now = _now()
        job = Job(
            id=uuid.uuid4().hex[:12], sample=sample, execution_mode=execution_mode,
            status="queued", stage="queued", created_at=now, updated_at=now,
        )
        with self._lock:
            self._connection.execute(
                "INSERT INTO jobs (id, sample, execution_mode, status, stage, error, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (job.id, job.sample, job.execution_mode, job.status, job.stage, None, now, now),
            )
            self._connection.commit()
        return job

    def update(self, job_id: str, *, status: JobStatus | None = None, stage: str | None = None,
               error: str | None = None) -> None:
        current = self.get(job_id)
        if current is None:
            raise KeyError(job_id)
        with self._lock:
            self._connection.execute(
                "UPDATE jobs SET status = ?, stage = ?, error = ?, updated_at = ? WHERE id = ?",
                (status or current.status, stage or current.stage, error, _now(), job_id),
            )
            self._connection.commit()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return Job.model_validate(dict(row)) if row else None

    def list(self, limit: int = 50) -> list[Job]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [Job.model_validate(dict(row)) for row in rows]

    def has_active(self, execution_mode: ExecutionMode) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM jobs WHERE execution_mode = ? AND status IN ('queued', 'running') LIMIT 1",
                (execution_mode,),
            ).fetchone()
        return row is not None

    def fail_orphans(self) -> None:
        """Marca como fallidos los jobs que quedaron a medias si el proceso se reinició."""
        with self._lock:
            self._connection.execute(
                "UPDATE jobs SET status = 'failed', error = 'Interrumpido por reinicio del servidor',"
                " updated_at = ? WHERE status IN ('queued', 'running')",
                (_now(),),
            )
            self._connection.commit()
