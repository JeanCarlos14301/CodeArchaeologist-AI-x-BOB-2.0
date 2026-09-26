"""Pruebas del grafo de llamadas y del lector de fuentes del sandbox (api/graph.py)."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import graph as graph_api

JOB_ID = "job-graph-1"

BILLING = '''DISCOUNT = 0.1


def calculate(total):
    return total * DISCOUNT


def invoice_total(items):
    return calculate(sum(items))
'''

APP = '''from billing import invoice_total


def create_app():
    def invoice_json(invoice_id):
        return invoice_total([invoice_id])

    invoice_json = route_get("/invoices/<int:invoice_id>")(invoice_json)
    return invoice_json
'''

RESULT = {
    "selected_first_cut": "GET /invoices/{id}",
    "findings": [
        {
            "id": "F-1", "title": "Descuento duplicado", "severity": "HIGH", "status": "accepted",
            "blast_radius_score": 40.0,
            "evidence": [
                {"path": "billing.py", "line_start": 5, "line_end": 5, "fragment": "return total * DISCOUNT"},
                {"path": "billing.py", "line_start": 1, "line_end": 1, "fragment": "DISCOUNT = 0.1"},
            ],
            "transitive_impacted_symbols": ["billing.invoice_total", "billing.no_existe"],
        }
    ],
    "migration_summary": {
        "modern_code_files": ["modern/api.py"], "facade_router_file": "facade.py",
        "legacy_tests_verdict": "PASS", "modern_tests_verdict": "PASS",
        "diff_patch": "--- a/app.py\n+++ b/modern/api.py\n-old\n+new\n+newer\n",
    },
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo = tmp_path / "sandboxes" / JOB_ID / "repo"
    (repo / "modern").mkdir(parents=True)
    (repo / "billing.py").write_text(BILLING, encoding="utf-8")
    (repo / "app.py").write_text(APP, encoding="utf-8")
    (repo / "modern" / "api.py").write_text("def get_invoice():\n    return 1\n", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("no debe leerse", encoding="utf-8")

    monkeypatch.setattr(graph_api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(graph_api, "get_job", lambda job_id: {"id": job_id, "status": "completed"} if job_id == JOB_ID else None)
    monkeypatch.setattr(graph_api, "get_job_result", lambda job_id: RESULT)

    app = FastAPI()
    app.include_router(graph_api.router)
    return TestClient(app)


def test_graph_nodes_and_edges_come_from_real_ast(client: TestClient) -> None:
    body = client.get(f"/api/jobs/{JOB_ID}/graph").json()
    ids = {node["id"] for node in body["nodes"]}
    assert {"billing.py::calculate", "billing.py::invoice_total", "app.py::create_app.invoice_json"} <= ids
    assert {"source": "billing.py::invoice_total", "target": "billing.py::calculate"} in body["edges"]
    assert {"source": "app.py::create_app.invoice_json", "target": "billing.py::invoice_total"} in body["edges"]
    assert next(n for n in body["nodes"] if n["id"] == "modern/api.py::get_invoice")["kind"] == "modern"


def test_findings_map_to_enclosing_function_or_module(client: TestClient) -> None:
    body = client.get(f"/api/jobs/{JOB_ID}/graph").json()
    nodes = {mark["node"] for mark in body["findings"]}
    assert nodes == {"billing.py::calculate", "billing.py::<module>"}
    assert any(n["id"] == "billing.py::<module>" for n in body["nodes"])


def test_blast_radius_reports_unresolved_symbols_instead_of_inventing_nodes(client: TestClient) -> None:
    blast = client.get(f"/api/jobs/{JOB_ID}/graph").json()["blast_radius"][0]
    assert blast["impacted_nodes"] == ["billing.py::invoice_total"]
    assert blast["unresolved_symbols"] == ["billing.no_existe"]


def test_migration_cut_counts_diff_lines(client: TestClient) -> None:
    cut = client.get(f"/api/jobs/{JOB_ID}/graph").json()["migration_cut"]
    assert (cut["diff_added"], cut["diff_removed"]) == (2, 1)
    assert cut["modern_nodes"] == ["modern/api.py::get_invoice"]


def test_unknown_job_is_404(client: TestClient) -> None:
    assert client.get("/api/jobs/otro/graph").status_code == 404


def test_source_reads_lines_and_blocks_path_traversal(client: TestClient) -> None:
    ok = client.get(f"/api/jobs/{JOB_ID}/source", params={"path": "billing.py", "start": 1, "end": 2}).json()
    assert [line["number"] for line in ok["lines"]] == [1, 2]
    assert ok["lines"][0]["text"] == "DISCOUNT = 0.1"
    assert client.get(f"/api/jobs/{JOB_ID}/source", params={"path": "../../secret.txt"}).status_code == 404
    assert client.get(f"/api/jobs/{JOB_ID}/source", params={"path": "/etc/passwd"}).status_code == 404
