"""Pruebas de la carga de ZIP y de las vistas reales (api/live.py). No gastan bobcoins.

Bob se sustituye por la respuesta real grabada en contracts/fixtures; el resto (extracción segura,
validación de evidencia, grafo, arquitectura) es el código de producción.
"""

import io
import time
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.bob_adapter import BobAdapter
from app.jobs import service as service_module
from app.main import create_app
from app.pipeline.evidence_audit import AUDITOR_MODE, DOSSIER_FILE, build_dossier, prepare_workspace

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "samples" / "facturaya-v1"
RECORDED_BOB = REPO_ROOT / "contracts" / "fixtures" / "bob-evidence-auditor-facturaya.json"
TOKEN = "token-de-prueba"


def _zip_of_sample() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in SAMPLE.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".sqlite3":
                archive.write(path, f"facturaya/{path.relative_to(SAMPLE).as_posix()}")
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("LIVE_AUDIT_TOKEN", TOKEN)

    def recorded_audit(source_repo: Path, job_dir: Path, on_stage=lambda _s: None, **_kwargs):
        workspace = prepare_workspace(source_repo, job_dir)
        result = BobAdapter.import_result(RECORDED_BOB, AUDITOR_MODE)
        dossier = build_dossier(source_repo.name, workspace, result)
        (job_dir / DOSSIER_FILE).write_text(dossier.model_dump_json(), encoding="utf-8")
        return dossier

    monkeypatch.setattr(service_module, "run_evidence_audit", recorded_audit)
    app = create_app(artifacts_dir=tmp_path / "artifacts", frontend_dist=tmp_path / "no-dist")
    with TestClient(app) as test_client:
        yield test_client


def _upload(client: TestClient, data: bytes, token: str | None = TOKEN, name: str = "repo.zip"):
    headers = {"X-Live-Token": token} if token else {}
    return client.post("/api/audits/upload", files={"zip_file": (name, data, "application/zip")}, headers=headers)


def _wait_done(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        detail = client.get(f"/api/audits/{job_id}").json()
        if detail["job"]["status"] in {"done", "failed"}:
            return detail
        time.sleep(0.05)
    raise AssertionError("la auditoría no terminó")


def test_token_is_always_required(client: TestClient) -> None:
    data = _zip_of_sample()
    assert _upload(client, data, token=None).status_code == 403
    assert _upload(client, data, token="otro").status_code == 403


def test_uploads_are_refused_when_server_has_no_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIVE_AUDIT_TOKEN")
    assert _upload(client, _zip_of_sample(), token="lo-que-sea").status_code == 503


def test_rejects_non_zip_and_unsafe_zip(client: TestClient) -> None:
    assert _upload(client, b"no soy un zip").status_code == 400
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../escape.py", "x = 1")
    job = _upload(client, buffer.getvalue()).json()
    detail = _wait_done(client, job["id"])
    assert detail["job"]["status"] == "failed"
    assert "ZipSlip" in detail["job"]["error"] or "no permitida" in detail["job"]["error"]


def test_upload_runs_live_audit_and_returns_validated_dossier(client: TestClient) -> None:
    response = _upload(client, _zip_of_sample())
    assert response.status_code == 202
    job = response.json()
    assert job["execution_mode"] == "live"
    detail = _wait_done(client, job["id"])
    assert detail["job"]["status"] == "done"
    # El expediente refleja el modo de la respuesta de Bob; aquí es la grabación real, por eso "imported".
    assert detail["dossier"]["stats"]["evidence_valid_ratio"] == 1.0


def test_graph_and_architecture_are_measured_on_uploaded_code(client: TestClient) -> None:
    job_id = _upload(client, _zip_of_sample()).json()["id"]
    _wait_done(client, job_id)

    graph = client.get(f"/api/audits/{job_id}/graph").json()
    assert graph["has_result"] and graph["nodes"] and graph["edges"]
    assert graph["migration_cut"] is None
    assert all(mark["node"] for mark in graph["findings"])
    assert all(item["score"] is None for item in graph["blast_radius"])

    architecture = client.get(f"/api/audits/{job_id}/architecture").json()
    assert architecture["totals"]["functions"] == len(collect_names(graph))
    assert architecture["mermaid"].startswith("flowchart LR")
    assert architecture["sql"]["total"] >= architecture["sql"]["concatenated"]
    assert architecture["routes"] and architecture["complex_functions"]


def collect_names(graph: dict) -> list[str]:
    return [node["id"] for node in graph["nodes"] if node["qualname"] != "<module>"]


def test_downloads_are_limited_to_dossier_and_bob_result(client: TestClient) -> None:
    job_id = _upload(client, _zip_of_sample()).json()["id"]
    _wait_done(client, job_id)
    assert client.get(f"/api/audits/{job_id}/files/dossier.json").status_code == 200
    assert client.get(f"/api/audits/{job_id}/files/..%2Fjobs.db").status_code == 404
    assert client.get(f"/api/audits/{job_id}/files/workspace").status_code == 404
