"""Modernization Studio: validators, the full assess -> plan -> implement flow and the API. No real Bob."""

import io
import json
import shutil
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.adapters.bob_adapter import BobExecutionError, BobResult, BobStats
from app.jobs.service import AuditService
from app.main import create_app
from app.modernization.models import AssessRequest, Mapping
from app.modernization.planner import PlannerError, validate_assessment, validate_plan
from app.modernization.stack_scan import scan_stack
from app.modernization.studio import Studio, StudioBusyError, StudioStateError

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "samples" / "facturaya-v1"
TOKEN = "test-token"


def _tradeoffs(extra: dict | None = None) -> list[dict]:
    items = [
        {"axis": "security", "effect": "improves", "detail": "Typed input validation on every route.", "refs": [{"path": "app.py", "line_start": 1, "line_end": 3}]},
        {"axis": "performance", "effect": "improves", "detail": "Asynchronous server with no blocking per request.", "refs": []},
        {"axis": "team", "effect": "worsens", "detail": "The team has to learn a new asynchronous model.", "refs": []},
    ]
    if extra:
        items.append(extra)
    return items


def _assessment(**overrides) -> dict:
    data = {
        "verdict": "conditional",
        "summary": "Migrating gradually pays off if tests cover it first.",
        "business_reading": "The system bills customers: security weighs more than delivery speed.",
        "tradeoffs": _tradeoffs(),
        "blockers": ["Characterization tests are missing."],
        "questions": [],
        "recommended": [],
    }
    data.update(overrides)
    return data


def _plan(**overrides) -> dict:
    data = {
        "summary": "Migrate layer by layer while keeping the observable behavior.",
        "rollback": "The original project is kept and the delivered ZIP is reverted.",
        "steps": [
            {"id": "S1", "title": "Dependencies", "kind": "dependencies", "why": "The new framework needs its packages.", "depends_on": [],
             "files": [{"path": "requirements.txt", "action": "modify"}], "risk": "low", "complexity": "low",
             "validation": "Install in a clean environment.", "changes": "Replace Flask with FastAPI and add uvicorn."},
            {"id": "S2", "title": "Application", "kind": "code", "why": "Rewrite the routes with the new framework.", "depends_on": ["S1"],
             "files": [{"path": "app.py", "action": "modify"}, {"path": "main_fastapi.py", "action": "create"}], "risk": "medium", "complexity": "high",
             "validation": "Compare responses with the legacy code.", "changes": "Create main_fastapi.py with the equivalent routes."},
        ],
    }
    data.update(overrides)
    return data


@pytest.fixture(scope="module")
def stack():
    return scan_stack(SAMPLE)


# ------------------------------------------------------------ validators

def test_assessment_verifies_code_references(stack) -> None:
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    assessment = validate_assessment(_assessment(), request, stack, SAMPLE)
    assert assessment.tradeoffs[0].refs[0].verified is True
    bad = _tradeoffs()
    bad[0]["refs"] = [{"path": "missing.py", "line_start": 1, "line_end": 2}]
    assert validate_assessment(_assessment(tradeoffs=bad), request, stack, SAMPLE).tradeoffs[0].refs[0].verified is False


@pytest.mark.parametrize("patch,message", [
    ({"tradeoffs": [{"axis": "cost", "effect": "neutral", "detail": "License cost unchanged.", "refs": []}] * 3}, "security and performance"),
    ({"summary": "It improves performance by 40% with no effort at all."}, "figures"),
    ({"business_reading": "It is solved in two weeks of team work."}, "figures"),
    ({"verdict": "recommended", "blockers": ["Coverage is missing."]}, "blockers"),
])
def test_assessment_rejects_invalid_answers(stack, patch: dict, message: str) -> None:
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    with pytest.raises(PlannerError, match=message):
        validate_assessment(_assessment(**patch), request, stack, SAMPLE)


def test_recommend_mode_only_accepts_catalog_targets_of_detected_tech(stack) -> None:
    request = AssessRequest(mode="recommend")
    ok = _assessment(recommended=[{"from_id": "flask", "to_id": "fastapi", "why": "Typed validation and async support."}])
    assert validate_assessment(ok, request, stack, SAMPLE).recommended[0].to_id == "fastapi"
    for from_id, to_id in (("express", "fastify"), ("flask", "react"), ("flask", "invented")):
        bad = _assessment(recommended=[{"from_id": from_id, "to_id": to_id, "why": "Just because, with no other reason."}])
        with pytest.raises(PlannerError):
            validate_assessment(bad, request, stack, SAMPLE)


def test_plan_rejects_cycles_missing_files_and_bad_paths() -> None:
    assert len(validate_plan(_plan(), SAMPLE).steps) == 2
    steps = _plan()["steps"]
    steps[0]["depends_on"] = ["S2"]
    with pytest.raises(PlannerError, match="circular dependencies"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[0]["files"] = [{"path": "missing.txt", "action": "modify"}]
    with pytest.raises(PlannerError, match="does not exist"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[1]["files"] = [{"path": "app.py", "action": "create"}]
    with pytest.raises(PlannerError, match="already exists"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[0]["files"] = [{"path": "../outside.py", "action": "create"}]
    with pytest.raises(PlannerError, match="not allowed"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[0]["changes"] = "It takes about three weeks of work in total."
    with pytest.raises(PlannerError, match="figures"):
        validate_plan(_plan(steps=steps), SAMPLE)


# ------------------------------------------------------------ full flow with a simulated Bob

class FakeBob:
    """Stands in for Bob: answers the requested JSON and, as the surgeon, edits the working copy."""

    def __init__(self, work: Path, kind: str, calls: list[str], break_python: bool = False, fail_step: str | None = None) -> None:
        self.work, self.kind, self.calls = work, kind, calls
        self.break_python, self.fail_step = break_python, fail_step

    def _result(self, payload: dict) -> BobResult:
        return BobResult(mode=self.kind, status="success", last_message=json.dumps(payload),
                         stats=BobStats(task_id="t", duration_ms=10, session_costs=0.05), execution_mode="live")

    def run(self, mode: str, prompt: str) -> BobResult:
        self.calls.append(mode)
        if mode == "modernization-planner":
            return self._result(_plan() if "STEPS ALREADY DONE" not in prompt and "steps" in prompt and "rollback" in prompt and "PREVIOUS ASSESSMENT" in prompt else _assessment())
        step = "S1" if '"id": "S1"' in prompt else "S2"
        if step == self.fail_step:
            raise BobExecutionError("Bob was cut off")
        if step == "S1":
            (self.work / "requirements.txt").write_text("fastapi==0.110.0\nuvicorn==0.29.0\n", encoding="utf-8")
        else:
            code = "def broken(:\n" if self.break_python else "from fastapi import FastAPI\napp = FastAPI()\n"
            (self.work / "main_fastapi.py").write_text(code, encoding="utf-8")
            (self.work / "app.py").write_text("# migrated\n", encoding="utf-8")
            (self.work / "extra.py").write_text("x = 1\n", encoding="utf-8")  # outside the plan
        return self._result({"summary": f"Step {step} done."})


def _studio(tmp_path: Path, calls: list[str], **fake) -> Studio:
    job_dir = tmp_path / "job"
    shutil.copytree(SAMPLE, job_dir / "source", ignore=shutil.ignore_patterns("__pycache__", "*.sqlite3"))
    return Studio(job_dir, "facturaya.zip", adapter_factory=lambda work, kind: FakeBob(work, kind, calls, **fake))


def _run_all(studio: Studio) -> None:
    studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")], business_context="Electronic invoicing"))
    studio.run_assess()
    studio.begin_plan()
    studio.run_plan()
    studio.begin_implement()
    studio.run_implement()


def test_full_flow_delivers_zip_diff_and_measured_report(tmp_path: Path) -> None:
    calls: list[str] = []
    studio = _studio(tmp_path, calls)
    _run_all(studio)
    state = studio.state()
    assert state.phase == "implemented", state.error
    assert calls == ["modernization-planner", "modernization-planner", "modernization-surgeon", "modernization-surgeon"]
    result = state.implementation
    assert result is not None and [s.status for s in result.steps] == ["done", "done"]
    assert {c.path for s in result.steps for c in s.changed} == {"requirements.txt", "main_fastapi.py", "app.py", "extra.py"}
    assert result.outside_plan == ["extra.py"]  # measured by code, not declared by Bob
    assert all(check.ok for check in result.checks) and {c.kind for c in result.checks} == {"python"}
    assert result.lines_added > 0 and result.lines_removed > 0 and "neither run" in result.not_executed
    with zipfile.ZipFile(studio.artifact("modernized.zip")) as archive:
        names = archive.namelist()
        assert "facturaya-modernized/main_fastapi.py" in names
        assert not any(".bob" in name for name in names)
        assert archive.read("facturaya-modernized/requirements.txt").startswith(b"fastapi")
    assert "+from fastapi import FastAPI" in studio.artifact("migration.diff").read_text(encoding="utf-8")
    assert (SAMPLE / "requirements.txt").read_text(encoding="utf-8").startswith("Flask"), "the original is left alone"


def test_syntax_errors_in_generated_code_are_reported(tmp_path: Path) -> None:
    studio = _studio(tmp_path, [], break_python=True)
    _run_all(studio)
    checks = studio.state().implementation.checks
    assert [c.path for c in checks if not c.ok] == ["main_fastapi.py"]


def test_a_failed_step_skips_the_rest_and_keeps_what_was_done(tmp_path: Path) -> None:
    studio = _studio(tmp_path, [], fail_step="S2")
    _run_all(studio)
    state = studio.state()
    assert state.phase == "implemented"
    assert [s.status for s in state.implementation.steps] == ["done", "failed"]


def test_all_steps_failing_is_a_failure(tmp_path: Path) -> None:
    studio = _studio(tmp_path, [], fail_step="S1")
    studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")]))
    studio.run_assess()
    studio.begin_plan()
    studio.run_plan()
    studio.begin_implement()
    studio.run_implement()
    state = studio.state()
    assert state.phase == "failed" and "did not complete any step" in state.error


def test_phase_rules_and_request_validation(tmp_path: Path) -> None:
    studio = _studio(tmp_path, [])
    with pytest.raises(StudioStateError):
        studio.begin_plan()
    with pytest.raises(StudioStateError):
        studio.begin_implement()
    with pytest.raises(StudioStateError, match="Pick at least"):
        studio.begin_assess(AssessRequest(mode="chosen"))
    with pytest.raises(StudioStateError, match="detected technologies"):
        studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="express", to_id="fastify")]))
    with pytest.raises(StudioStateError, match="possible target"):
        studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="react")]))
    studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")]))
    with pytest.raises(StudioBusyError):
        studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")]))


# ------------------------------------------------------------ API

def _zip_of(root: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".sqlite3":
                archive.write(path, f"project/{path.relative_to(root).as_posix()}")
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LIVE_AUDIT_TOKEN", TOKEN)
    calls: list[str] = []
    monkeypatch.setattr(AuditService, "modernize_adapter_factory", lambda self, work, kind: FakeBob(work, kind, calls))
    app = create_app(artifacts_dir=tmp_path / "artifacts", frontend_dist=tmp_path / "no-dist")
    with TestClient(app) as test_client:
        test_client.calls = calls  # type: ignore[attr-defined]
        yield test_client


def _wait(client: TestClient, job_id: str, phases: set[str]) -> dict:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        state = client.get(f"/api/audits/{job_id}/modernization", headers={"X-Live-Token": TOKEN}).json()
        if state["phase"] in phases:
            return state
        time.sleep(0.05)
    raise AssertionError(f"did not reach {phases}")


def test_modernization_upload_needs_no_bob_and_works_for_any_stack(client: TestClient, tmp_path: Path) -> None:
    headers = {"X-Live-Token": TOKEN}
    node = tmp_path / "node-app"
    (node / "src").mkdir(parents=True)
    (node / "package.json").write_text(json.dumps({"dependencies": {"express": "4.18.2"}}), encoding="utf-8")
    (node / "src" / "index.js").write_text("const express = require('express')\n", encoding="utf-8")
    response = client.post("/api/audits/upload", files={"zip_file": ("api.zip", _zip_of(node), "application/zip")}, data={"purpose": "modernization"}, headers=headers)
    assert response.status_code == 202 and response.json()["sample"] == "modernize:api.zip"
    job_id = response.json()["id"]
    for _ in range(100):
        if client.get(f"/api/audits/{job_id}", headers=headers).json()["job"]["status"] == "done":
            break
        time.sleep(0.05)
    stack = client.get(f"/api/audits/{job_id}/modernization/stack", headers=headers).json()
    assert {"express", "javascript"} <= {t["id"] for t in stack["technologies"]}
    assert "fastify" in {t["id"] for t in stack["targets"]["express"]}
    assert client.get(f"/api/audits/{job_id}/modernization/stack").status_code == 403, "it is private: it requires the token"


def test_api_full_flow_with_token_and_confirmation(client: TestClient) -> None:
    headers = {"X-Live-Token": TOKEN}
    job_id = client.post("/api/audits/upload", files={"zip_file": ("f.zip", _zip_of(SAMPLE), "application/zip")}, data={"purpose": "modernization"}, headers=headers).json()["id"]
    for _ in range(100):
        if client.get(f"/api/audits/{job_id}", headers=headers).json()["job"]["status"] == "done":
            break
        time.sleep(0.05)
    base = f"/api/audits/{job_id}/modernization"
    body = {"mode": "chosen", "mappings": [{"from_id": "flask", "to_id": "fastapi"}], "business_context": "Invoicing", "priorities": ["security"]}
    assert client.post(f"{base}/assess", json=body).status_code == 403, "without a token Bob is not invoked"
    assert client.post(f"{base}/assess", json={**body, "mappings": [{"from_id": "flask", "to_id": "react"}]}, headers=headers).status_code == 422
    assert client.post(f"{base}/assess", json=body, headers=headers).status_code == 202
    assert _wait(client, job_id, {"assessed", "failed"})["phase"] == "assessed"
    assert client.post(f"{base}/implement", json={"confirm": True}, headers=headers).status_code == 409, "the plan is needed first"
    assert client.post(f"{base}/plan", headers=headers).status_code == 202
    assert _wait(client, job_id, {"planned", "failed"})["phase"] == "planned"
    assert client.post(f"{base}/implement", json={"confirm": False}, headers=headers).status_code == 422
    assert client.post(f"{base}/implement", json={"confirm": True}, headers=headers).status_code == 202
    state = _wait(client, job_id, {"implemented", "failed"})
    assert state["phase"] == "implemented", state["error"]
    assert client.get(f"{base}/download/modernized.zip").status_code == 403
    download = client.get(f"{base}/download/modernized.zip", headers=headers)
    assert download.status_code == 200 and download.content[:2] == b"PK"
    assert client.get(f"{base}/download/state.json", headers=headers).status_code == 404
    assert "workspace" not in json.dumps(state) and str(SAMPLE) not in json.dumps(state)


# ------------------------------------------------------------ real activity, retry with feedback and fixes

def test_percent_in_code_is_legitimate_but_percent_figures_are_not(stack) -> None:
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    sql = _tradeoffs()
    sql[0]["detail"] = "The search concatenates `WHERE number LIKE '%" + "' + q + '" + "%'` without parameters (app.py lines 78-79)."
    assert validate_assessment(_assessment(tradeoffs=sql), request, stack, SAMPLE).tradeoffs[0].axis == "security"
    with pytest.raises(PlannerError, match="figures"):
        validate_assessment(_assessment(summary="It improves performance by 40 % with the change."), request, stack, SAMPLE)


def test_assessment_lists_fixes_and_checks_them(stack) -> None:
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    ok = _assessment(fixes_during_migration=["SQL injection in the invoice search (app.py:78)."])
    assert validate_assessment(ok, request, stack, SAMPLE).fixes_during_migration
    with pytest.raises(PlannerError, match="figures"):
        validate_assessment(_assessment(fixes_during_migration=["Fixed in three weeks."]), request, stack, SAMPLE)


class StreamingBob(FakeBob):
    """Like the real Bob: emits stream-json events while it works and, the first time, answers something invalid."""

    def __init__(self, *args, first_invalid: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.first_invalid = first_invalid
        self.asked = 0

    def run_stream(self, mode: str, prompt: str, on_event, **_kwargs) -> BobResult:
        on_event({"type": "tool_use", "tool_name": "read_file", "parameters": {"path": "app.py"}, "tool_id": "t1"})
        on_event({"type": "tool_use", "tool_name": "search_files", "parameters": {"regex": "execute", "path": "."}, "tool_id": "t2"})
        if mode == "modernization-surgeon":
            on_event({"type": "tool_use", "tool_name": "write_to_file", "parameters": {"path": "main_fastapi.py"}, "tool_id": "t3"})
        self.asked += 1
        if self.first_invalid and self.asked == 1:
            return self._result({"verdict": "conditional"})  # incomplete: the validator rejects it
        return self.run(mode, prompt)


def test_studio_shows_what_bob_is_really_doing(tmp_path: Path) -> None:
    calls: list[str] = []
    job_dir = tmp_path / "job"
    shutil.copytree(SAMPLE, job_dir / "source", ignore=shutil.ignore_patterns("__pycache__", "*.sqlite3"))
    made: list[StreamingBob] = []

    def factory(work: Path, kind: str) -> StreamingBob:
        made.append(StreamingBob(work, kind, calls, first_invalid=True))
        return made[-1]

    studio = Studio(job_dir, "f.zip", adapter_factory=factory)
    studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")]))
    studio.run_assess()
    state = studio.state()
    assert state.phase == "assessed", state.error
    titles = [e.message for e in state.events if e.phase == "assessing"]
    assert any(t.startswith("Copying the project") for t in titles)
    assert "Read app.py" in titles and any(t.startswith("Searched «execute»") for t in titles)
    assert any(e.kind == "validator" for e in state.events), "the validator's rejection and the retry are visible"
    assert made[0].asked == 2, "Bob corrected its reply with the rejection reason"
    assert all("workspace" not in json.dumps(e.model_dump()) for e in state.events)

    studio.begin_plan()
    studio.run_plan()
    studio.begin_implement()
    studio.run_implement()
    edits = [e for e in studio.state().events if e.kind == "bob.edit"]
    assert edits and edits[0].message == "Wrote main_fastapi.py" and edits[0].step_id in {"S1", "S2"}


def test_bob_failure_is_not_retried_with_feedback(tmp_path: Path) -> None:
    calls: list[str] = []
    job_dir = tmp_path / "job"
    shutil.copytree(SAMPLE, job_dir / "source", ignore=shutil.ignore_patterns("__pycache__", "*.sqlite3"))

    class Broken(FakeBob):
        def run(self, mode: str, prompt: str):
            self.calls.append(mode)
            raise BobExecutionError("down")

    studio = Studio(job_dir, "f.zip", adapter_factory=lambda work, kind: Broken(work, kind, calls))
    studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")]))
    studio.run_assess()
    assert studio.state().phase == "failed" and calls == ["modernization-planner"]


def test_surgeon_reports_the_security_fixes_it_made(tmp_path: Path) -> None:
    class Fixing(FakeBob):
        def run(self, mode: str, prompt: str):
            result = super().run(mode, prompt)
            if mode == "modernization-surgeon":
                payload = json.loads(result.last_message)
                payload["fixed"] = ["Invoice search parameterized (it used to concatenate SQL)."]
                return self._result(payload)
            return result

    calls: list[str] = []
    studio = _studio(tmp_path, calls)
    studio.adapter_factory = lambda work, kind: Fixing(work, kind, calls)
    _run_all(studio)
    steps = studio.state().implementation.steps
    assert steps[0].fixed == ["Invoice search parameterized (it used to concatenate SQL)."]


def test_known_audit_findings_reach_the_planner(tmp_path: Path) -> None:
    studio = _studio(tmp_path, [])
    dossier = json.loads((REPO_ROOT / "contracts" / "fixtures" / "valid-dossier.json").read_text(encoding="utf-8")) if (REPO_ROOT / "contracts" / "fixtures" / "valid-dossier.json").is_file() else None
    assert studio.findings_digest() == "[]"
    if dossier and {"findings", "stats", "evidence_checks"} <= dossier.keys():
        (studio.job_dir / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
        digest = json.loads(studio.findings_digest())
        assert digest and {"id", "severity", "title", "where"} <= digest[0].keys()


def test_chosen_mode_ignores_recommendations_instead_of_rejecting(stack) -> None:
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    echoed = _assessment(recommended=[{"from_id": "flask", "to_id": "fastapi", "why": "It fits the team better."}])
    assert validate_assessment(echoed, request, stack, SAMPLE).recommended == []


# ------------------------------------------------------------ the person's answers to Bob's questions

def test_answers_reach_both_prompts_and_are_limited(stack) -> None:
    from app.modernization.models import Answer
    from app.modernization.planner import build_assess_prompt, build_plan_prompt

    answers = [Answer(question="Will the system run in containers?", answer="Yes, a single server with Docker.")]
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")], answers=answers)
    assert "a single server with Docker" in build_assess_prompt(stack, request)
    assessment = validate_assessment(_assessment(), request, stack, SAMPLE)
    assert "a single server with Docker" in build_plan_prompt(stack, request, assessment)
    with pytest.raises(Exception):
        AssessRequest(mode="recommend", answers=[Answer(question="Question number %d?" % i, answer="yes") for i in range(11)])


def test_studio_keeps_answers_across_reassessments(tmp_path: Path) -> None:
    from app.modernization.models import Answer

    studio = _studio(tmp_path, [])
    first = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    studio.begin_assess(first)
    studio.run_assess()
    again = first.model_copy(update={"answers": [Answer(question="Are there external customers?", answer="I don't know")]})
    studio.begin_assess(again)
    studio.run_assess()
    state = studio.state()
    assert state.phase == "assessed" and state.request.answers[0].answer == "I don't know"
    assert state.plan is None, "assessing again discards the previous plan"


def test_assistant_also_works_on_modernization_only_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api import assistant

    seen: dict[str, Path] = {}
    monkeypatch.setenv("LIVE_AUDIT_TOKEN", TOKEN)
    def fake_ask(workspace: Path, body) -> assistant.AskAnswer:
        seen["workspace"] = workspace
        return assistant.AskAnswer(summary="Test answer without the real Bob.")

    monkeypatch.setattr(assistant, "ask_bob", fake_ask)
    app = create_app(artifacts_dir=tmp_path / "artifacts", frontend_dist=tmp_path / "no-dist")
    with TestClient(app) as client:
        headers = {"X-Live-Token": TOKEN}
        job_id = client.post("/api/audits/upload", files={"zip_file": ("f.zip", _zip_of(SAMPLE), "application/zip")}, data={"purpose": "modernization"}, headers=headers).json()["id"]
        for _ in range(100):
            if client.get(f"/api/audits/{job_id}", headers=headers).json()["job"]["status"] == "done":
                break
            time.sleep(0.05)
        client.post(f"/api/audits/{job_id}/ask", json={"question": "What should be migrated first?"}, headers=headers)
    assert seen["workspace"].name == "source", "without an audit, Bob reads the project's full copy"


def test_concurrent_requests_start_a_single_bob_operation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import threading

    studio = _studio(tmp_path, [])
    studio.stack()
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    original_state = Studio.state

    def slow_state(self: Studio):
        state = original_state(self)
        time.sleep(0.02)  # widens the window between reading the phase and writing it (double click, retries)
        return state

    monkeypatch.setattr(Studio, "state", slow_state)
    outcomes: list[str] = []
    barrier = threading.Barrier(4)

    def attempt() -> None:
        barrier.wait()
        try:
            studio.begin_assess(request)
            outcomes.append("started")
        except StudioBusyError:
            outcomes.append("busy")

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["busy", "busy", "busy", "started"]
