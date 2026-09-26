"""Actividad en vivo del análisis: intérprete del stream de Bob, streaming real, cierre por presupuesto
y endpoint de eventos. Bob se sustituye por un ejecutable falso: no se gastan bobcoins."""

import json
import stat
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.bob_adapter import BobAdapter, BobExecutionError, BobResult, BobRunSettings, BobStats, BobTimeoutError
from app.pipeline.activity import BobActivity, EventLog, parse_todos, read_events, relative_to_workspace
from app.pipeline.evidence_audit import AUDITOR_MODE, FINALIZE_PROMPT, audit_with_bob, prepare_workspace

REPO_ROOT = Path(__file__).resolve().parents[2]
FINDINGS_JSON = json.dumps({"findings": [{
    "id": "F-1", "title": "SQL concatenado", "category": "security", "subcategory": "sql-injection",
    "severity": "critical", "observed_or_inferred": "observed",
    "evidence": [{"path": "app.py", "line_start": 2, "line_end": 2, "snippet": "sql = 'SELECT ' + q"}],
    "explanation": "La entrada se concatena en el SQL.", "recommendation": "Parametrizar la consulta.",
}]})


def _ts(offset: float) -> str:
    base = 1_790_000_000 + offset
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(base))) + f".{int(round(base % 1 * 1000)):03d}Z"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "app.py").write_text("import sqlite3\nsql = 'SELECT ' + q\n")
    return root


def _events(log: EventLog) -> list:
    return read_events(log.path)


# --- Intérprete ---------------------------------------------------------------------------

def test_activity_translates_plan_tools_subagents_and_turns(workspace: Path, tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    activity = BobActivity(log, workspace)
    stream = [
        {"type": "cost", "costs": {"input": 100, "output": 5}},
        {"type": "cost", "costs": {"input": 100, "output": 5}},  # repetido: no es un turno nuevo
        {"type": "message", "role": "assistant", "content": "Voy a leer el punto de entrada "},
        {"type": "message", "role": "assistant", "content": f"en {workspace}/app.py."},
        {"type": "tool_use", "tool_name": "update_todo_list", "parameters": {"todos": "[x] Fase 1\n[-] Fase 2: subagentes\n[ ] Fase 3"}},
        {"type": "tool_use", "tool_name": "read_file", "parameters": {"path": str(workspace / "app.py")}},
        {"type": "tool_use", "tool_name": "read_file", "parameters": {"path": "/etc/passwd"}},
        {"type": "tool_use", "tool_name": "use_skill", "parameters": {"skill_name": "legacy-audit-workflow"}},
        {"type": "tool_use", "tool_name": "spawn_subagent", "parameters": {"name": "legacy-sql-auditor"}},
        {"type": "subagent_start", "agentType": "legacy-sql-auditor", "description": f"Audita SQL en {workspace}/app.py"},
        {"type": "subagent_end", "metadata": {"agentType": "legacy-sql-auditor", "toolUseCount": 7, "loopTurnCount": 4,
                                              "durationMs": 9000, "spend": {"cost": 0.42}, "loopExitReason": "stop"}},
        {"type": "cost", "costs": {"input": 250, "output": 40}},
        {"type": "message", "role": "assistant", "content": FINDINGS_JSON},
        {"type": "result", "status": "success", "stats": {"session_costs": 0.9, "max_cost": 4.0, "duration_ms": 12000, "tool_calls": 5}},
    ]
    for event in stream:
        activity.feed(event)

    events = _events(log)
    kinds = [event.kind for event in events]
    assert kinds.count("bob.turn") == 2
    thinking = next(event for event in events if event.kind == "bob.thinking")
    assert str(workspace) not in (thinking.detail or "")
    plan = next(event for event in events if event.kind == "bob.plan")
    assert [item["state"] for item in plan.data["items"]] == ["done", "active", "pending"]
    reads = [event.title for event in events if event.kind == "bob.tool"]
    assert reads == ["Leyó app.py", "Leyó passwd"], "nunca se exponen rutas del servidor"
    assert "bob.skill" in kinds
    start = next(event for event in events if event.kind == "bob.subagent.start")
    assert start.data["agent"] == "legacy-sql-auditor" and str(workspace) not in (start.detail or "")
    end = next(event for event in events if event.kind == "bob.subagent.end")
    assert end.data["cost"] == 0.42 and end.data["tool_uses"] == 7
    assert "bob.answer" in kinds, "el JSON final no se muestra como razonamiento"
    assert events[-1].kind == "bob.result" and events[-1].data["cost"] == 0.9
    assert all(event.stage == "auditing" for event in events)


def test_activity_reports_progress_while_writing_the_dossier(workspace: Path, tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    activity = BobActivity(log, workspace)
    activity.feed({"type": "message", "role": "assistant", "content": '{"findings": ['})
    for _ in range(9):
        activity.feed({"type": "message", "role": "assistant", "content": "x" * 500})
    writing = [event for event in _events(log) if event.kind == "bob.writing"]
    assert [event.data["chars"] for event in writing] == [2000, 4000]
    assert all("xxx" not in (event.detail or "") for event in writing), "no se expone el contenido"


def test_parse_todos_ignores_noise() -> None:
    assert parse_todos("titulo\n[x] uno\n  [-] dos\n[ ] tres\nsin marca") == [
        {"state": "done", "text": "uno"}, {"state": "active", "text": "dos"}, {"state": "pending", "text": "tres"},
    ]


def test_relative_to_workspace_hides_server_paths(workspace: Path) -> None:
    assert relative_to_workspace(str(workspace / "a" / "b.py"), workspace) == "a/b.py"
    assert relative_to_workspace(str(workspace), workspace) == "."
    assert relative_to_workspace("/home/otro/secreto.py", workspace) == "secreto.py"
    assert relative_to_workspace("lib/x.py", workspace) == "lib/x.py"


def test_recorded_session_keeps_original_rhythm(workspace: Path, tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    activity = BobActivity(log, workspace, recorded=True, clock=10.0)
    activity.feed({"type": "tool_use", "tool_name": "read_file", "parameters": {"path": "app.py"}, "timestamp": _ts(0)})
    activity.feed({"type": "tool_use", "tool_name": "read_file", "parameters": {"path": "db.py"}, "timestamp": _ts(42.5)})
    first, second = _events(log)
    assert (first.t, second.t) == (10.0, 52.5)
    assert first.recorded and second.recorded


def test_event_log_cursor_and_sequence(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    for i in range(5):
        log.emit("preparing", "x", "python", f"evento {i}")
    assert [event.seq for event in read_events(log.path, after=3)] == [4, 5]
    assert EventLog(log.path).emit("done", "y", "python", "sigue").seq == 6, "reabrir continúa la secuencia"


# --- Streaming real con un ejecutable falso ------------------------------------------------

FAKE_BOB = r'''#!{python}
import json, os, sys, time
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
args = sys.argv[1:]
prompt = sys.stdin.read()
scenario = os.environ.get("FAKE_BOB_SCENARIO", "ok")
def out(event):
    print(json.dumps(event), flush=True)
if scenario == "sleep":
    time.sleep(5)
if scenario == "crash":
    print("boom interno /Users/secreto", file=sys.stderr); sys.exit(3)
if scenario == "cut" and "--resume" not in args:
    out({{"type": "message", "role": "user", "content": prompt}})
    out({{"type": "tool_use", "tool_name": "read_file", "parameters": {{"path": "app.py"}}}})
    print("Unexpected error: terminated", file=sys.stderr); sys.exit(1)
log_dir = os.environ.get("BOB_LOG_DIR")
if log_dir and scenario == "ok":
    from datetime import datetime, timezone
    def stamp():
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    workspace = args[args.index("--workspace") + 1]
    with open(os.path.join(log_dir, "bob-shell-20990101T000000.log"), "w") as log:
        log.write(json.dumps({{"ts": stamp(), "module": "workspace", "msg": "detectPath resolved: " + workspace}}) + "\n")
        start = {{"type": "subagent_start", "agentType": "legacy-sql-auditor", "description": "Audita SQL"}}
        end = {{"type": "subagent_end", "metadata": {{"agentType": "legacy-sql-auditor", "toolUseCount": 3, "spend": {{"cost": 0.2}}}}}}
        noise = {{"type": "message", "role": "assistant", "content": "no debe duplicarse"}}
        for event in (start, noise, end):
            log.write(json.dumps({{"ts": stamp(), "module": "stream-json-renderer", "msg": json.dumps(event)}}) + "\n")
        log.flush()
if "--resume" in args:
    out({{"type": "message", "role": "user", "content": "prompt original"}})
    out({{"type": "tool_use", "tool_name": "read_file", "parameters": {{"path": "viejo.py"}}}})
    out({{"type": "message", "role": "user", "content": prompt}})
    out({{"type": "message", "role": "assistant", "content": {findings!r}}})
    out({{"type": "result", "status": "success", "stats": {{"task_id": "t1", "duration_ms": 900, "session_costs": 4.3, "tool_calls": 3}}}})
    sys.exit(0)
out({{"type": "message", "role": "user", "content": prompt}})
out({{"type": "message", "role": "assistant", "content": "Primero exploro. "}})
out({{"type": "tool_use", "tool_name": "glob", "parameters": {{"pattern": "**/*.py"}}}})
out({{"type": "tool_result", "status": "success", "output": "app.py"}})
final = {findings!r} if scenario == "ok" else "No files found"
out({{"type": "message", "role": "assistant", "content": final}})
out({{"type": "result", "status": "success", "stats": {{"task_id": "t1", "duration_ms": 1500, "session_costs": 4.02, "max_cost": 4.0, "tool_calls": 3}}}})
'''


@pytest.fixture
def fake_bob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    if sys.platform == "win32":
        py_script = tmp_path / "fake_bob.py"
        py_script.write_text(FAKE_BOB.format(python=sys.executable, findings=FINDINGS_JSON), encoding="utf-8")
        cmd_script = tmp_path / "bob.cmd"
        cmd_script.write_text(f'@"{sys.executable}" "{py_script}" %*\n', encoding="utf-8")
        script = cmd_script
    else:
        script = tmp_path / "bob"
        script.write_text(FAKE_BOB.format(python=sys.executable, findings=FINDINGS_JSON))
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("BOB_API_KEY", "test-key")
    return script


def _adapter(workspace: Path, fake_bob: Path, **overrides) -> BobAdapter:
    settings = BobRunSettings(**{"bob_binary": str(fake_bob), "max_cost": 5.0, "timeout_s": 20, **overrides})
    return BobAdapter(workspace, settings, frozenset({AUDITOR_MODE}))


def test_run_stream_forwards_events_and_rebuilds_final_message(workspace: Path, fake_bob: Path) -> None:
    seen: list[str] = []
    result = _adapter(workspace, fake_bob).run_stream(AUDITOR_MODE, "audita", lambda event: seen.append(event["type"]))
    assert seen == ["message", "message", "tool_use", "tool_result", "message", "result"]
    assert result.last_message == FINDINGS_JSON, "solo cuenta el texto posterior a la última herramienta"
    assert result.stats is not None and result.stats.session_costs == 4.02


def test_run_stream_merges_real_time_subagent_events_from_bobs_log(workspace: Path, fake_bob: Path, tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "bob-shell-19990101T000000.log").write_text("otra sesión de otro workspace\n")
    monkeypatch.setenv("BOB_LOG_DIR", str(log_dir))
    seen: list[dict] = []
    raw = tmp_path / "raw.jsonl"
    _adapter(workspace, fake_bob).run_stream(AUDITOR_MODE, "audita", seen.append, raw_log=raw)
    types = [event["type"] for event in seen]
    assert "subagent_start" in types and "subagent_end" in types
    assert types.count("message") == 3, "los mensajes del log no se duplican con los de stdout"
    assert all("timestamp" in event for event in seen if event["type"].startswith("subagent"))
    assert "subagent_end" in raw.read_text(), "la sesión cruda también guarda los eventos del log"


def test_run_stream_resume_skips_replayed_history(workspace: Path, fake_bob: Path) -> None:
    seen: list[dict] = []
    result = _adapter(workspace, fake_bob).run_stream(AUDITOR_MODE, FINALIZE_PROMPT, seen.append, resume_task_id="t1")
    assert all(event.get("parameters", {}).get("path") != "viejo.py" for event in seen)
    assert result.last_message == FINDINGS_JSON


def test_run_stream_timeout_and_crash(workspace: Path, fake_bob: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_BOB_SCENARIO", "sleep")
    with pytest.raises(BobTimeoutError):
        _adapter(workspace, fake_bob, timeout_s=1).run_stream(AUDITOR_MODE, "audita", lambda _e: None)
    monkeypatch.setenv("FAKE_BOB_SCENARIO", "crash")
    with pytest.raises(BobExecutionError):
        _adapter(workspace, fake_bob).run_stream(AUDITOR_MODE, "audita", lambda _e: None)


def test_active_sessions_are_terminated_on_shutdown(workspace: Path, fake_bob: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import threading

    from app.adapters.bob_adapter import terminate_active_sessions

    monkeypatch.setenv("FAKE_BOB_SCENARIO", "sleep")
    errors: list[Exception] = []

    def run() -> None:
        try:
            _adapter(workspace, fake_bob, timeout_s=30).run_stream(AUDITOR_MODE, "audita", lambda _e: None)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    deadline = time.monotonic() + 5
    while terminate_active_sessions() == 0 and time.monotonic() < deadline:
        time.sleep(0.05)
    worker.join(10)
    assert not worker.is_alive()
    assert errors and isinstance(errors[0], BobExecutionError)


def test_audit_finalizes_when_budget_runs_out(workspace: Path, fake_bob: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_BOB_SCENARIO", "no-json")
    log = EventLog(tmp_path / "events.jsonl")
    result = audit_with_bob(_adapter(workspace, fake_bob), workspace, tmp_path, log)
    assert json.loads(result.last_message)["findings"][0]["id"] == "F-1"
    assert result.stats is not None and result.stats.duration_ms == 2400 and result.stats.session_costs == 4.3
    kinds = [event.kind for event in read_events(log.path)]
    assert kinds[0] == "bob.start" and "bob.finalize" in kinds
    start = read_events(log.path)[0]
    assert start.data["explore_cost"] == 4.0, "se reserva parte del tope para el cierre"
    assert (tmp_path / "bob-stream.jsonl").is_file()


def test_audit_resumes_a_session_cut_by_the_network(workspace: Path, fake_bob: Path, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    import sqlite3

    database = tmp_path / "bob.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE tasks (id TEXT, parent_id TEXT, env TEXT, created_at INTEGER)")
        connection.execute("INSERT INTO tasks VALUES ('otra', NULL, ?, 1)", (json.dumps({"workspace": "/otro"}),))
        connection.execute("INSERT INTO tasks VALUES ('t1', NULL, ?, 2)", (json.dumps({"workspace": str(workspace.resolve())}),))
    monkeypatch.setenv("BOB_DB_PATH", str(database))
    monkeypatch.setenv("FAKE_BOB_SCENARIO", "cut")
    log = EventLog(tmp_path / "events.jsonl")
    result = audit_with_bob(_adapter(workspace, fake_bob), workspace, tmp_path, log)
    assert json.loads(result.last_message)["findings"][0]["id"] == "F-1"
    finalize = next(event for event in read_events(log.path) if event.kind == "bob.finalize")
    assert finalize.data["reason"] == "interrupted"


def test_cut_without_a_recoverable_session_reports_the_error(workspace: Path, fake_bob: Path, tmp_path: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOB_DB_PATH", str(tmp_path / "no-existe.db"))
    monkeypatch.setenv("FAKE_BOB_SCENARIO", "cut")
    with pytest.raises(BobExecutionError):
        audit_with_bob(_adapter(workspace, fake_bob), workspace, tmp_path, None)


def test_audit_without_streaming_adapter_still_works(workspace: Path, tmp_path: Path) -> None:
    class Plain:
        settings = BobRunSettings()

        def run(self, mode: str, prompt: str) -> BobResult:
            return BobResult(mode=mode, status="success", last_message=FINDINGS_JSON,
                             stats=BobStats(task_id="t", duration_ms=1, session_costs=0.1), execution_mode="live")

    assert audit_with_bob(Plain(), workspace, tmp_path, None).last_message == FINDINGS_JSON


def test_uploads_keep_their_tests_but_samples_do_not(tmp_path: Path) -> None:
    source = tmp_path / "src"
    (source / "tests").mkdir(parents=True)
    (source / "tests" / "test_app.py").write_text("def test_x(): ...\n")
    (source / "app.py").write_text("x = 1\n")
    assert (prepare_workspace(source, tmp_path / "upload", keep_tests=True) / "tests" / "test_app.py").is_file()
    assert not (prepare_workspace(source, tmp_path / "sample") / "tests").exists()


# --- Endpoint -----------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    from app.main import create_app

    monkeypatch.setenv("LIVE_AUDIT_TOKEN", "token-de-prueba")
    app = create_app(artifacts_dir=tmp_path / "artifacts", frontend_dist=tmp_path / "no-dist")
    with TestClient(app) as test_client:
        yield test_client


def _wait(client: TestClient, job_id: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if client.get(f"/api/audits/{job_id}").json()["job"]["status"] in {"done", "failed"}:
            return
        time.sleep(0.05)
    raise AssertionError("el job no terminó a tiempo")


def test_events_endpoint_covers_every_stage_of_the_showcase(client: TestClient) -> None:
    job_id = client.post("/api/audits", json={"sample": "facturaya-v1", "execution_mode": "imported"}).json()["id"]
    _wait(client, job_id)
    page = client.get(f"/api/audits/{job_id}/events").json()
    stages = {event["stage"] for event in page["events"]}
    assert {"preparing", "auditing", "validating", "migration", "done"} <= stages
    kinds = {event["kind"] for event in page["events"]}
    assert {"inventory", "evidence.check", "evidence.summary", "tests.result", "dossier.ready"} <= kinds
    inventory = next(event for event in page["events"] if event["kind"] == "inventory")
    assert inventory["data"]["files"] > 0 and inventory["data"]["languages"][0]["name"] == "Python"
    rest = client.get(f"/api/audits/{job_id}/events", params={"after": page["next_after"]}).json()
    assert rest["events"] == []


def test_events_endpoint_unknown_job_is_404(client: TestClient) -> None:
    assert client.get("/api/audits/nope/events").status_code == 404
