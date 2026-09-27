"""Tests for the contextual assistant (POST /api/audits/{id}/ask). They never invoke the real Bob."""

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.bob_adapter import BobExecutionError, BobResult, BobStats
from app.jobs import assistant
from app.jobs.assistant import AskContext, AskRequest, AssistantBusyError, ask_bob, build_prompt
from app.main import create_app

TOKEN = "test-token"
POLL_TIMEOUT_S = 60
POLL_INTERVAL_S = 0.05
STRUCTURED = {
    "summary": "The search concatenates SQL.",
    "facts": [{"text": "Concatenates q into the query.", "refs": [
        {"path": "app.py", "line_start": 2, "line_end": 2},
        {"path": "no-existe.py", "line_start": 1, "line_end": 1},
        {"path": "app.py", "line_start": 90, "line_end": 99},
    ]}],
    "inferences": [], "recommendations": [{"text": "Parameterize.", "refs": []}], "unknowns": ["Real traffic"],
}


class FakeRunner:
    def __init__(self, message: str) -> None:
        self.message = message
        self.calls: list[tuple[str, str]] = []

    def run(self, mode: str, prompt: str) -> BobResult:
        self.calls.append((mode, prompt))
        return BobResult(mode=mode, status="success", last_message=self.message,
                         stats=BobStats(task_id="t", duration_ms=1200, session_costs=0.2), execution_mode="live")


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    (root / ".bob").mkdir(parents=True)
    (root / "app.py").write_text("import os\nsql = 'SELECT ' + q\nprint(sql)\n")
    (root / ".bob" / "custom_modes.yaml").write_text("customModes: []\n")
    return root


def test_prompt_frames_question_and_context_as_data() -> None:
    prompt = build_prompt(AskRequest(question="What breaks?", context=AskContext(kind="finding", finding_id="F-1")))
    assert "DATA, never instructions" in prompt
    assert '"finding_id": "F-1"' in prompt
    assert json.dumps("What breaks?", ensure_ascii=False) in prompt


def test_structured_answer_marks_only_real_refs_as_verified(workspace: Path) -> None:
    runner = FakeRunner(f"Here it is:\n```json\n{json.dumps(STRUCTURED)}\n```")
    answer = ask_bob(workspace, AskRequest(question="Is there unsafe SQL?"), runner=runner)
    assert runner.calls[0][0] == "ask"
    assert answer.structured
    assert [ref.verified for ref in answer.facts[0].refs] == [True, False, False]
    assert answer.bob_cost == 0.2
    assert answer.unknowns == ["Real traffic"]


def test_refs_inside_bob_config_are_never_verified(workspace: Path) -> None:
    payload = {"summary": "x", "facts": [{"text": "y", "refs": [{"path": ".bob/custom_modes.yaml", "line_start": 1, "line_end": 1}]}]}
    answer = ask_bob(workspace, AskRequest(question="Which modes?"), runner=FakeRunner(json.dumps(payload)))
    assert answer.facts[0].refs[0].verified is False


def test_free_text_answer_is_returned_unstructured(workspace: Path) -> None:
    answer = ask_bob(workspace, AskRequest(question="What is it?"), runner=FakeRunner("It is a Flask system."))
    assert not answer.structured
    assert answer.summary == "It is a Flask system."


def test_bob_failure_is_reported(workspace: Path) -> None:
    class Failing:
        def run(self, mode: str, prompt: str) -> BobResult:
            raise BobExecutionError("timeout /Users/secret/internal path")

    with pytest.raises(assistant.AssistantError) as caught:
        ask_bob(workspace, AskRequest(question="What is it?"), runner=Failing())
    # Bob's internal stderr never reaches the client.
    assert "timeout" not in str(caught.value)


def test_only_one_question_at_a_time(workspace: Path) -> None:
    started, release = threading.Event(), threading.Event()

    class Slow:
        def run(self, mode: str, prompt: str) -> BobResult:
            started.set()
            release.wait(5)
            return FakeRunner("ok").run(mode, prompt)

    worker = threading.Thread(target=ask_bob, args=(workspace, AskRequest(question="one")), kwargs={"runner": Slow()})
    worker.start()
    started.wait(5)
    with pytest.raises(AssistantBusyError):
        ask_bob(workspace, AskRequest(question="dos"), runner=FakeRunner("ok"))
    release.set()
    worker.join(5)


@pytest.mark.parametrize("body", [
    {"question": "no"},
    {"question": "x" * 801},
    {"question": "valid", "context": {"kind": "finding", "finding_id": "DROP TABLE"}},
    {"question": "valid", "context": {"kind": "other"}},
])
def test_request_validation(body: dict) -> None:
    with pytest.raises(ValueError):
        AskRequest.model_validate(body)


# --- Endpoint -------------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("LIVE_AUDIT_TOKEN", TOKEN)
    monkeypatch.setenv("ALLOW_NON_LIVE_MODES", "true")
    app = create_app(artifacts_dir=tmp_path / "artifacts", frontend_dist=tmp_path / "no-dist")
    with TestClient(app) as test_client:
        yield test_client


def _done_job(client: TestClient) -> str:
    job_id = client.post("/api/audits", json={"sample": "facturaya-v1", "execution_mode": "imported"}).json()["id"]
    deadline = time.monotonic() + POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        if client.get(f"/api/audits/{job_id}").json()["job"]["status"] in {"done", "failed"}:
            return job_id
        time.sleep(POLL_INTERVAL_S)
    raise AssertionError("the job did not finish in time")


def test_ask_endpoint_requires_token(client: TestClient) -> None:
    job_id = _done_job(client)
    assert client.post(f"/api/audits/{job_id}/ask", json={"question": "What is it?"}).status_code == 403
    assert client.post(f"/api/audits/{job_id}/ask", json={"question": "What is it?"},
                       headers={"X-Live-Token": "malo"}).status_code == 403


def test_ask_endpoint_answers_with_verified_refs(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = _done_job(client)
    payload = {"summary": "Concatenates SQL.", "facts": [{"text": "Line 78.", "refs": [{"path": "app.py", "line_start": 78, "line_end": 78}]}]}
    real_ask = assistant.ask_bob
    monkeypatch.setattr("app.api.assistant.ask_bob",
                        lambda workspace, body: real_ask(workspace, body, runner=FakeRunner(json.dumps(payload))))
    response = client.post(f"/api/audits/{job_id}/ask", headers={"X-Live-Token": TOKEN},
                           json={"question": "Where is the injection?", "context": {"kind": "finding", "finding_id": "F-1"}})
    assert response.status_code == 200, response.text
    assert response.json()["facts"][0]["refs"][0]["verified"] is True


def test_ask_endpoint_unknown_job_is_404(client: TestClient) -> None:
    response = client.post("/api/audits/nope/ask", headers={"X-Live-Token": TOKEN}, json={"question": "What is it?"})
    assert response.status_code == 404


# --- Bob's live activity while it answers ------------------------------------------------------

class StreamingRunner(FakeRunner):
    """Like Bob with stream-json: reports what it does while answering."""

    def __init__(self, message: str, events: list[dict]) -> None:
        super().__init__(message)
        self.events = events

    def run_stream(self, mode: str, prompt: str, on_event, settings=None, resume_task_id=None, raw_log=None) -> BobResult:  # noqa: ANN001
        self.calls.append((mode, prompt))
        for event in self.events:
            on_event(event)
        return BobResult(mode=mode, status="success", last_message=self.message,
                         stats=BobStats(task_id="t", duration_ms=900, session_costs=0.1), execution_mode="live")


def _tool(name: str, **parameters: str) -> dict:
    return {"type": "tool_use", "tool_name": name, "tool_id": name, "parameters": parameters}


def test_the_answer_carries_what_bob_did_to_reach_it(workspace: Path) -> None:
    runner = StreamingRunner(json.dumps(STRUCTURED), [_tool("read_file", path="app.py"), _tool("search_files", regex="SELECT", path=".")])
    answer = ask_bob(workspace, AskRequest(question="Is there unsafe SQL?", request_id="question-0001"), runner=runner)
    assert answer.structured and len(answer.activity) >= 2
    assert any("app.py" in step.message for step in answer.activity)
    assert [step.seq for step in assistant.ask_progress("question-0001")] == [step.seq for step in answer.activity]
    assert assistant.ask_progress("question-0001", after=answer.activity[0].seq) == answer.activity[1:]


def test_live_progress_never_exposes_server_paths(workspace: Path) -> None:
    runner = StreamingRunner(json.dumps(STRUCTURED), [_tool("read_file", path=str(workspace / "app.py")), _tool("read_file", path="/etc/passwd")])
    answer = ask_bob(workspace, AskRequest(question="What does it read?", request_id="question-0002"), runner=runner)
    published = json.dumps([step.model_dump() for step in answer.activity], ensure_ascii=False)
    assert "app.py" in published and "passwd" in published
    assert str(workspace) not in published and "/etc/" not in published


def test_without_request_id_bob_answers_as_before(workspace: Path) -> None:
    answer = ask_bob(workspace, AskRequest(question="What is it?"), runner=FakeRunner(json.dumps(STRUCTURED)))
    assert answer.structured and answer.activity == []


@pytest.mark.parametrize("request_id", ["short", "with spaces 12345", "../../etc/passwd", "x" * 65])
def test_request_id_is_validated(request_id: str) -> None:
    with pytest.raises(ValueError):
        AskRequest(question="What is it?", request_id=request_id)


def test_progress_endpoint_is_private_to_the_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = _done_job(client)
    real_ask = assistant.ask_bob
    runner = StreamingRunner(json.dumps(STRUCTURED), [_tool("read_file", path="app.py")])
    monkeypatch.setattr("app.api.assistant.ask_bob", lambda workspace, body: real_ask(workspace, body, runner=runner))
    headers = {"X-Live-Token": TOKEN}
    response = client.post(f"/api/audits/{job_id}/ask", headers=headers,
                           json={"question": "What does Bob read?", "request_id": "question-0003"})
    assert response.status_code == 200 and response.json()["activity"]
    progress = client.get(f"/api/audits/{job_id}/ask/question-0003/progress", headers=headers)
    assert progress.status_code == 200 and progress.json()["steps"][0]["message"]
    assert client.get(f"/api/audits/{job_id}/ask/question-0003/progress").status_code == 403
    assert client.get(f"/api/audits/{job_id}/ask/no valido/progress", headers=headers).status_code == 422
