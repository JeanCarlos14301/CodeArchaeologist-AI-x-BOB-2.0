"""Primer corte de referencia ejecutado solo sobre muestras registradas del equipo."""

import shutil
from pathlib import Path

from app.contracts.schema_v1 import MigrationResult, MigrationTestResult
from app.sandbox.migration_runner import apply_strangler_cut
from app.sandbox.test_runner import run_pytest_in_sandbox

MIGRATION_DIFF_FILE = "migration.diff"
SANDBOX_DIR = "migration-sandbox"
MODERN_TEST = '''"""Contrato del primer corte de referencia; ejecutado contra FastAPI."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import modern.invoices_api as invoices_api
from seed import seed


def client_for(tmp_path, monkeypatch):
    database = tmp_path / "modern.sqlite3"
    seed(database)
    original = invoices_api.get_db_connection
    monkeypatch.setattr(invoices_api, "get_db_connection", lambda: original(str(database)))
    app = FastAPI()
    app.include_router(invoices_api.router)
    return TestClient(app)


def test_first_invoice_exact_contract(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    response = client.get("/invoices/1", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    assert response.json() == {
        "id": 1, "number": "FY-00001", "customer": {"id": 1, "name": "Cliente Demo 01"},
        "date": "2024-01-01", "items": [
            {"description": "Caso redondeo A", "quantity": 1, "unit_price": "50.03", "line_total": "50.03"},
            {"description": "Caso redondeo B", "quantity": 1, "unit_price": "50.04", "line_total": "50.04"},
        ], "subtotal": "100.07", "discount": "7.51", "total": "92.56", "status": "paid",
    }


def test_contract_errors_and_bola_fix(tmp_path, monkeypatch):
    client = client_for(tmp_path, monkeypatch)
    assert client.get("/invoices/1").status_code == 401
    assert client.get("/invoices/9999", headers={"X-User-ID": "1"}).status_code == 404
    assert client.get("/invoices/1", headers={"X-User-ID": "2"}).status_code == 404
'''


def _convert(report: object, target: str) -> list[MigrationTestResult]:
    return [MigrationTestResult(
        name=test.name,
        target=target,
        status={"PASS": "passed", "FAIL": "failed"}.get(test.status, "not_run"),
        duration_ms=test.duration_ms,
        reason=test.error_message,
    ) for test in report.test_cases]


def not_run_result(reason: str) -> MigrationResult:
    return MigrationResult(
        status="not_run",
        reason=reason,
        implementation_origin="Implementación de referencia del equipo; no generada por Bob.",
        endpoint="GET /invoices/{id}",
    )


def run_reference_cut(source_repo: Path, job_dir: Path, modern_code: str | None = None) -> MigrationResult:
    """Copia y ejecuta solo la muestra controlada; nunca recibe un ZIP del visitante."""
    sandbox = job_dir / SANDBOX_DIR
    if sandbox.exists():
        shutil.rmtree(sandbox)
    shutil.copytree(
        source_repo,
        sandbox,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.sqlite3", ".pytest_cache"),
    )

    legacy_contract = run_pytest_in_sandbox(sandbox, "tests/test_invoice_contract.py")
    legacy_rules = run_pytest_in_sandbox(sandbox, "tests/test_business_rules.py")
    apply_strangler_cut(sandbox, modern_code=modern_code)
    modern_test = sandbox / "tests" / "test_modern_invoice_contract.py"
    modern_test.write_text(MODERN_TEST, encoding="utf-8")
    modern = run_pytest_in_sandbox(sandbox, "tests/test_modern_invoice_contract.py")

    tests = _convert(legacy_contract, "legacy") + _convert(legacy_rules, "legacy") + _convert(modern, "modern")
    status = "passed" if tests and all(test.status == "passed" for test in tests) else "failed"
    shutil.copy2(sandbox / MIGRATION_DIFF_FILE, job_dir / MIGRATION_DIFF_FILE)
    return MigrationResult(
        status=status,
        reason=None if status == "passed" else "Una o más pruebas reales de caracterización fallaron.",
        implementation_origin="Implementación de referencia del equipo; no generada por Bob.",
        endpoint="GET /invoices/{id}",
        tests=tests,
        legacy_file="app.py",
        modern_file="modern/invoices_api.py",
        facade_file="facade.py",
        diff_file=MIGRATION_DIFF_FILE,
    )
