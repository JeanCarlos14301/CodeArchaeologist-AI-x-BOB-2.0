"""Pruebas de integración de la API REST de Auditorías y Migración (D-02, D-07, D-08)."""

from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app.database import init_db
from backend.app.main import app

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "bob_shell_available" in data
    assert "execution_mode" in data


def test_samples_endpoint(client: TestClient):
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert isinstance(samples, list)
    assert any(s["id"] == "facturaya-v1" for s in samples)


def test_audits_list_endpoint(client: TestClient):
    response = client.get("/api/audits")
    assert response.status_code == 200
    audits = response.json()
    assert isinstance(audits, list)


def test_migration_endpoint_facturaya_if_available(client: TestClient):
    """Valida que /api/audits/{id}/migration devuelva la recomendación determinista completa."""
    audits_res = client.get("/api/audits")
    assert audits_res.status_code == 200
    audits = audits_res.json()
    if not audits:
        return

    job_id = audits[0]["id"]
    res = client.get(f"/api/audits/{job_id}/migration")
    if res.status_code == 200:
        data = res.json()
        assert "job_id" in data
        assert "result" in data
        assert "candidates" in data
        assert "recommended" in data
        assert "waves" in data
        assert "first_cut_pert" in data
        if data["candidates"]:
            assert len(data["candidates"]) >= 3
            rec = data["recommended"]
            assert "score" in rec
            assert "formula" in rec
            assert "why" in rec
            assert "findings_mitigated" in rec
            # Validar que el PERT incluya la advertencia de no calibrado
            first_pert = data["first_cut_pert"]
            assert first_pert is not None
            assert any("no calibrada" in a.lower() for a in first_pert.get("assumptions", []))
