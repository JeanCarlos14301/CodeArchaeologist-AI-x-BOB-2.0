"""Endurecimiento de lo que se publica: rutas del servidor, errores de Bob, límites del registro de
actividad y arranque concurrente de auditorías live. No gasta bobcoins."""

import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.bob_adapter import BobExecutionError, BobResult, BobTimeoutError
from app.jobs.service import BusyError
from app.main import create_app
from app.pipeline import activity as activity_module
from app.pipeline.activity import BobActivity, EventLog, parse_todos, read_events, redact_paths
from app.pipeline.evidence_audit import AuditError, run_evidence_audit

SERVER_PATH = "/Users/operador/proyectos/codearch/backend/artifacts/abc123/workspace/app.py"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "app.py").write_text("import sqlite3\nsql = 'SELECT ' + q\n")
    return root


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(artifacts_dir=tmp_path / "artifacts", frontend_dist=tmp_path / "no-dist")
    with TestClient(app) as test_client:
        yield test_client


# --- Rutas del servidor ---------------------------------------------------------------------

@pytest.mark.parametrize(("text", "expected"), [
    (f"No se pudo leer {SERVER_PATH}", "No se pudo leer app.py"),
    ("fallo en /tmp/pytest-7/job/", "fallo en …"),
    (r"C:\Users\operador\repo\db.py no existe", "db.py no existe"),
    ("ver https://example.com/docs/api y lib/x.py", "ver https://example.com/docs/api y lib/x.py"),
    ("ruta relativa app/routes.py:12 y fracción 3/4", "ruta relativa app/routes.py:12 y fracción 3/4"),
])
def test_redact_paths_keeps_only_the_final_name(text: str, expected: str) -> None:
    assert redact_paths(text) == expected


def test_tool_errors_and_plan_items_never_expose_server_paths(workspace: Path, tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    activity = BobActivity(log, workspace)
    activity.feed({"type": "tool_use", "tool_name": "update_todo_list",
                   "parameters": {"todos": f"[x] Leer {SERVER_PATH}\n[ ] Revisar /etc/secreto/config.ini"}})
    activity.feed({"type": "tool_result", "tool_id": "t1", "status": "error",
                   "output": f"ENOENT: no such file {SERVER_PATH}"})

    published = " ".join(f"{event.title} {event.detail or ''} {event.data}" for event in read_events(log.path))
    assert "/Users/" not in published and "/etc/" not in published
    assert "app.py" in published and "config.ini" in published


def test_failure_message_is_published_without_server_paths(client: TestClient, tmp_path: Path) -> None:
    service = client.app.state.audit_service
    job = service.store.create("facturaya-v1", "example")
    events = service.events(job.id)

    service._fail(job, events, f"Falló la lectura de {SERVER_PATH}")

    stored = service.store.get(job.id)
    failure = next(event for event in read_events(events.path) if event.kind == "pipeline.failed")
    assert stored.status == "failed"
    assert stored.error == failure.detail == "Falló la lectura de app.py"


# --- Errores de Bob -------------------------------------------------------------------------

class _FailingBob:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def run(self, mode: str, prompt: str) -> BobResult:
        raise self.error


@pytest.mark.parametrize(("error", "expected"), [
    (BobExecutionError(f"exit 1; stderr: Traceback en {SERVER_PATH}, API key rechazada"), "no se pudo recuperar la sesión"),
    (BobTimeoutError(f"Bob excedió 900 s en {SERVER_PATH}"), "tiempo máximo"),
])
def test_bob_failures_reach_the_user_without_internal_details(workspace: Path, tmp_path: Path,
                                                              error: Exception, expected: str) -> None:
    with pytest.raises(AuditError) as failure:
        run_evidence_audit(workspace, tmp_path / "job", adapter=_FailingBob(error))

    message = str(failure.value)
    assert expected in message
    assert "stderr" not in message and "/Users/" not in message and "API key rechazada" not in message


# --- Límites del registro de actividad ------------------------------------------------------

def test_event_log_caps_noise_but_keeps_essential_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(activity_module, "MAX_EVENTS", 3)
    log = EventLog(tmp_path / "events.jsonl")
    for index in range(10):
        log.emit("auditing", "bob.tool", "evidence-auditor", f"Leyó el archivo {index}")
    log.emit("done", "dossier.ready", "pipeline", "Expediente listo")

    kinds = [event.kind for event in read_events(log.path)]
    assert kinds == ["bob.tool"] * 3 + ["dossier.ready"], "el ruido se corta; el cierre siempre llega"


def test_read_events_skips_delivered_lines_and_ignores_corrupt_ones(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    for index in range(4):
        log.emit("preparing", "x", "python", f"evento {index}")
    with log.path.open("a", encoding="utf-8") as handle:
        handle.write("{esto no es json}\n")
    log.emit("preparing", "x", "python", "después de la línea corrupta")

    assert [event.seq for event in read_events(log.path, after=2)] == [3, 4, 5]


def test_parse_todos_is_capped() -> None:
    items = parse_todos("\n".join(f"[ ] tarea {index}" for index in range(500)))
    assert len(items) == activity_module.MAX_TODOS


# --- Arranque concurrente -------------------------------------------------------------------

def test_concurrent_live_starts_launch_a_single_audit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = client.app.state.audit_service
    submitted: list[str] = []
    monkeypatch.setattr(service.executor, "submit", lambda _fn, job, *_args: submitted.append(job.id))
    original_has_active = service.store.has_active

    def slow_has_active(mode: str) -> bool:
        active = original_has_active(mode)
        time.sleep(0.05)  # ensancha la ventana entre comprobar y crear
        return active

    monkeypatch.setattr(service.store, "has_active", slow_has_active)
    outcomes: list[str] = []
    barrier = threading.Barrier(4)

    def attempt() -> None:
        barrier.wait()
        try:
            service.start("facturaya-v1", "live")
            outcomes.append("started")
        except BusyError:
            outcomes.append("busy")

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["busy", "busy", "busy", "started"]
    assert len(submitted) == 1
