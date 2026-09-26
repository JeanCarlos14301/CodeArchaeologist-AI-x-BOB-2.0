"""Estudio de modernización: validadores, flujo completo evaluar -> planificar -> implementar y API. Sin Bob real."""

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
TOKEN = "token-de-prueba"


def _tradeoffs(extra: dict | None = None) -> list[dict]:
    items = [
        {"axis": "security", "effect": "improves", "detail": "Validación de entrada tipada en cada ruta.", "refs": [{"path": "app.py", "line_start": 1, "line_end": 3}]},
        {"axis": "performance", "effect": "improves", "detail": "Servidor asíncrono sin bloqueo por petición.", "refs": []},
        {"axis": "team", "effect": "worsens", "detail": "El equipo debe aprender un modelo asíncrono nuevo.", "refs": []},
    ]
    if extra:
        items.append(extra)
    return items


def _assessment(**overrides) -> dict:
    data = {
        "verdict": "conditional",
        "summary": "Conviene migrar de forma gradual si se cubre antes con pruebas.",
        "business_reading": "El sistema factura a clientes: la seguridad pesa más que la velocidad de entrega.",
        "tradeoffs": _tradeoffs(),
        "blockers": ["Faltan pruebas de caracterización."],
        "questions": [],
        "recommended": [],
    }
    data.update(overrides)
    return data


def _plan(**overrides) -> dict:
    data = {
        "summary": "Se migra por capas manteniendo el comportamiento observable.",
        "rollback": "Se conserva el proyecto original y se revierte el ZIP entregado.",
        "steps": [
            {"id": "S1", "title": "Dependencias", "kind": "dependencies", "why": "El nuevo framework necesita sus paquetes.", "depends_on": [],
             "files": [{"path": "requirements.txt", "action": "modify"}], "risk": "low", "complexity": "low",
             "validation": "Instalar en un entorno limpio.", "changes": "Sustituir Flask por FastAPI y añadir uvicorn."},
            {"id": "S2", "title": "Aplicación", "kind": "code", "why": "Reescribir las rutas con el nuevo framework.", "depends_on": ["S1"],
             "files": [{"path": "app.py", "action": "modify"}, {"path": "main_fastapi.py", "action": "create"}], "risk": "medium", "complexity": "high",
             "validation": "Comparar respuestas con el legado.", "changes": "Crear main_fastapi.py con las rutas equivalentes."},
        ],
    }
    data.update(overrides)
    return data


@pytest.fixture(scope="module")
def stack():
    return scan_stack(SAMPLE)


# ------------------------------------------------------------ validadores

def test_assessment_verifies_code_references(stack) -> None:
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    assessment = validate_assessment(_assessment(), request, stack, SAMPLE)
    assert assessment.tradeoffs[0].refs[0].verified is True
    bad = _tradeoffs()
    bad[0]["refs"] = [{"path": "no_existe.py", "line_start": 1, "line_end": 2}]
    assert validate_assessment(_assessment(tradeoffs=bad), request, stack, SAMPLE).tradeoffs[0].refs[0].verified is False


@pytest.mark.parametrize("patch,message", [
    ({"tradeoffs": [{"axis": "cost", "effect": "neutral", "detail": "Costo de licencias sin cambios.", "refs": []}] * 3}, "seguridad y rendimiento"),
    ({"summary": "Mejora el rendimiento un 40% sin esfuerzo alguno."}, "cifras"),
    ({"business_reading": "Se resuelve en dos semanas de trabajo del equipo."}, "cifras"),
    ({"verdict": "recommended", "blockers": ["Falta cobertura."]}, "bloqueos"),
    ({"recommended": [{"from_id": "flask", "to_id": "fastapi", "why": "Encaja mejor con el equipo."}]}, "recommended"),
])
def test_assessment_rejects_invalid_answers(stack, patch: dict, message: str) -> None:
    request = AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")])
    with pytest.raises(PlannerError, match=message):
        validate_assessment(_assessment(**patch), request, stack, SAMPLE)


def test_recommend_mode_only_accepts_catalog_targets_of_detected_tech(stack) -> None:
    request = AssessRequest(mode="recommend")
    ok = _assessment(recommended=[{"from_id": "flask", "to_id": "fastapi", "why": "Validación tipada y asincronía."}])
    assert validate_assessment(ok, request, stack, SAMPLE).recommended[0].to_id == "fastapi"
    for from_id, to_id in (("express", "fastify"), ("flask", "react"), ("flask", "inventado")):
        bad = _assessment(recommended=[{"from_id": from_id, "to_id": to_id, "why": "Porque sí, sin más razón."}])
        with pytest.raises(PlannerError):
            validate_assessment(bad, request, stack, SAMPLE)


def test_plan_rejects_cycles_missing_files_and_bad_paths() -> None:
    assert len(validate_plan(_plan(), SAMPLE).steps) == 2
    steps = _plan()["steps"]
    steps[0]["depends_on"] = ["S2"]
    with pytest.raises(PlannerError, match="circulares"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[0]["files"] = [{"path": "no_existe.txt", "action": "modify"}]
    with pytest.raises(PlannerError, match="no existe"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[1]["files"] = [{"path": "app.py", "action": "create"}]
    with pytest.raises(PlannerError, match="ya existe"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[0]["files"] = [{"path": "../fuera.py", "action": "create"}]
    with pytest.raises(PlannerError, match="no permitida"):
        validate_plan(_plan(steps=steps), SAMPLE)
    steps = _plan()["steps"]
    steps[0]["changes"] = "Toma unas tres semanas de trabajo en total."
    with pytest.raises(PlannerError, match="cifras"):
        validate_plan(_plan(steps=steps), SAMPLE)


# ------------------------------------------------------------ flujo completo con un Bob simulado

class FakeBob:
    """Sustituye a Bob: responde el JSON pedido y, como cirujano, edita la copia de trabajo."""

    def __init__(self, work: Path, kind: str, calls: list[str], break_python: bool = False, fail_step: str | None = None) -> None:
        self.work, self.kind, self.calls = work, kind, calls
        self.break_python, self.fail_step = break_python, fail_step

    def _result(self, payload: dict) -> BobResult:
        return BobResult(mode=self.kind, status="success", last_message=json.dumps(payload),
                         stats=BobStats(task_id="t", duration_ms=10, session_costs=0.05), execution_mode="live")

    def run(self, mode: str, prompt: str) -> BobResult:
        self.calls.append(mode)
        if mode == "modernization-planner":
            return self._result(_plan() if "PASOS" not in prompt and "steps" in prompt and "rollback" in prompt and "EVALUACIÓN PREVIA" in prompt else _assessment())
        step = "S1" if '"id": "S1"' in prompt else "S2"
        if step == self.fail_step:
            raise BobExecutionError("Bob se cortó")
        if step == "S1":
            (self.work / "requirements.txt").write_text("fastapi==0.110.0\nuvicorn==0.29.0\n", encoding="utf-8")
        else:
            code = "def broken(:\n" if self.break_python else "from fastapi import FastAPI\napp = FastAPI()\n"
            (self.work / "main_fastapi.py").write_text(code, encoding="utf-8")
            (self.work / "app.py").write_text("# migrado\n", encoding="utf-8")
            (self.work / "extra.py").write_text("x = 1\n", encoding="utf-8")  # fuera del plan
        return self._result({"summary": f"Paso {step} hecho."})


def _studio(tmp_path: Path, calls: list[str], **fake) -> Studio:
    job_dir = tmp_path / "job"
    shutil.copytree(SAMPLE, job_dir / "source", ignore=shutil.ignore_patterns("__pycache__", "*.sqlite3"))
    return Studio(job_dir, "facturaya.zip", adapter_factory=lambda work, kind: FakeBob(work, kind, calls, **fake))


def _run_all(studio: Studio) -> None:
    studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="flask", to_id="fastapi")], business_context="Facturación electrónica"))
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
    assert result.outside_plan == ["extra.py"]  # medido por código, no declarado por Bob
    assert all(check.ok for check in result.checks) and {c.kind for c in result.checks} == {"python"}
    assert result.lines_added > 0 and result.lines_removed > 0 and "no se ejecutó" in result.not_executed
    with zipfile.ZipFile(studio.artifact("modernized.zip")) as archive:
        names = archive.namelist()
        assert "facturaya-modernizado/main_fastapi.py" in names
        assert not any(".bob" in name for name in names)
        assert archive.read("facturaya-modernizado/requirements.txt").startswith(b"fastapi")
    assert "+from fastapi import FastAPI" in studio.artifact("migration.diff").read_text(encoding="utf-8")
    assert (SAMPLE / "requirements.txt").read_text(encoding="utf-8").startswith("Flask"), "el original no se toca"


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
    assert state.phase == "failed" and "ningún paso" in state.error


def test_phase_rules_and_request_validation(tmp_path: Path) -> None:
    studio = _studio(tmp_path, [])
    with pytest.raises(StudioStateError):
        studio.begin_plan()
    with pytest.raises(StudioStateError):
        studio.begin_implement()
    with pytest.raises(StudioStateError, match="Elige al menos"):
        studio.begin_assess(AssessRequest(mode="chosen"))
    with pytest.raises(StudioStateError, match="detectadas"):
        studio.begin_assess(AssessRequest(mode="chosen", mappings=[Mapping(from_id="express", to_id="fastify")]))
    with pytest.raises(StudioStateError, match="destino posible"):
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
                archive.write(path, f"proyecto/{path.relative_to(root).as_posix()}")
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
    raise AssertionError(f"no llegó a {phases}")


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
    assert client.get(f"/api/audits/{job_id}/modernization/stack").status_code == 403, "es privado: exige token"


def test_api_full_flow_with_token_and_confirmation(client: TestClient) -> None:
    headers = {"X-Live-Token": TOKEN}
    job_id = client.post("/api/audits/upload", files={"zip_file": ("f.zip", _zip_of(SAMPLE), "application/zip")}, data={"purpose": "modernization"}, headers=headers).json()["id"]
    for _ in range(100):
        if client.get(f"/api/audits/{job_id}", headers=headers).json()["job"]["status"] == "done":
            break
        time.sleep(0.05)
    base = f"/api/audits/{job_id}/modernization"
    body = {"mode": "chosen", "mappings": [{"from_id": "flask", "to_id": "fastapi"}], "business_context": "Facturación", "priorities": ["security"]}
    assert client.post(f"{base}/assess", json=body).status_code == 403, "sin token no se invoca a Bob"
    assert client.post(f"{base}/assess", json={**body, "mappings": [{"from_id": "flask", "to_id": "react"}]}, headers=headers).status_code == 422
    assert client.post(f"{base}/assess", json=body, headers=headers).status_code == 202
    assert _wait(client, job_id, {"assessed", "failed"})["phase"] == "assessed"
    assert client.post(f"{base}/implement", json={"confirm": True}, headers=headers).status_code == 409, "antes hace falta el plan"
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
