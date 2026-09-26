"""Pruebas de integración de la API REST y ciclo de vida de Jobs (D-02, D-07)."""

import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app.database import init_db
from backend.app.main import app
from backend.app.worker import run_pipeline_for_job

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "bob_shell_available" in data
    assert "execution_mode" in data


def test_job_lifecycle_and_synchronous_pipeline():
    """Prueba completa del ciclo de vida: creación de job, ejecución de pipeline y consulta de resultado."""
    client = TestClient(app)

    # 1. Crear Job
    res = client.post("/api/jobs", json={"source_type": "demo"})
    assert res.status_code == 202
    data = res.json()
    job_id = data["job_id"]
    assert data["status"] == "queued"

    # 2. Consultar estado inmediato
    res_status = client.get(f"/api/jobs/{job_id}")
    assert res_status.status_code == 200
    assert res_status.json()["job_id"] == job_id

    # 3. Esperar que el pipeline asíncrono termine en background
    # En Windows y CI compartido, Word/pytest pueden tardar más de 25 s sin que el worker falle.
    # Stage 7 runs the real FacturaYa suite in a subprocess with its own 60 s timeout,
    # after ~20 s of earlier stages on a slow machine; 60 s total was not enough.
    max_wait = 150
    start_time = time.time()
    comp_data = {}
    while time.time() - start_time < max_wait:
        res_completed = client.get(f"/api/jobs/{job_id}")
        assert res_completed.status_code == 200
        comp_data = res_completed.json()
        if comp_data["status"] in ["completed", "completed_with_warnings", "failed"]:
            break
        time.sleep(0.4)

    # 4. Verificar estado final completado
    assert comp_data.get("status") == "completed", f"Job failed or incomplete: {comp_data}"
    assert comp_data.get("progress_percent") == 100
    assert len(comp_data.get("events", [])) >= 10

    # 5. Obtener DossierResult
    res_dossier = client.get(f"/api/jobs/{job_id}/result")
    assert res_dossier.status_code == 200
    dossier_data = res_dossier.json()
    assert dossier_data["schema_version"] == "1.0"
    assert len(dossier_data["findings"]) >= 7
    assert dossier_data["selected_first_cut"] == "GET /invoices/{id}"

    # 6. Endpoint de migración
    res_migrate = client.post(f"/api/jobs/{job_id}/migrate", json={"endpoint": "GET /invoices/{id}"})
    assert res_migrate.status_code == 200
    assert res_migrate.json()["status"] == "applied"

    # 7. Descarga de artefactos
    res_docx = client.get(f"/api/jobs/{job_id}/artifacts/docx")
    assert res_docx.status_code == 200
    assert len(res_docx.content) > 1000

    res_html = client.get(f"/api/jobs/{job_id}/artifacts/html")
    assert res_html.status_code == 200
    assert "CodeArchaeologist" in res_html.text

    res_pptx = client.get(f"/api/jobs/{job_id}/artifacts/pptx")
    assert res_pptx.status_code == 200
    assert len(res_pptx.content) > 1000

    res_diff = client.get(f"/api/jobs/{job_id}/artifacts/diff")
    assert res_diff.status_code == 200
    assert len(res_diff.content) > 0
