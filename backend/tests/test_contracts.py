"""Pruebas de validación de contratos JSON y modelos Pydantic v2 (D-01)."""

import json
from pathlib import Path
import pytest
from backend.app.models import DossierResult, Finding, EvidenceLocation

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTRACTS_DIR = BASE_DIR / "contracts"


def test_schema_json_exists_and_is_valid():
    schema_file = CONTRACTS_DIR / "schema-v1.json"
    assert schema_file.exists(), "schema-v1.json debe existir"
    data = json.loads(schema_file.read_text(encoding="utf-8"))
    assert "$defs" in data or "properties" in data
    assert data.get("title") == "DossierResult"


def test_valid_dossier_fixture_loads_successfully():
    fixture_file = CONTRACTS_DIR / "fixtures" / "valid-dossier.json"
    assert fixture_file.exists(), "valid-dossier.json debe existir"
    data = json.loads(fixture_file.read_text(encoding="utf-8"))

    dossier = DossierResult.model_validate(data)
    assert dossier.schema_version == "1.0"
    assert dossier.snapshot.sample_id == "facturaya-v1"
    assert len(dossier.findings) >= 7
    assert dossier.selected_first_cut == "GET /invoices/{id}"
    assert dossier.validation_report.fidelity_ratio == 1.0


def test_partial_dossier_fixture():
    partial_file = CONTRACTS_DIR / "fixtures" / "partial-dossier.json"
    assert partial_file.exists(), "partial-dossier.json debe existir"
    data = json.loads(partial_file.read_text(encoding="utf-8"))
    dossier = DossierResult.model_validate(data)
    assert dossier.job_id == "job-partial-facturaya-002"
    assert len(dossier.findings) >= 3
    assert dossier.characterization_tests_legacy is None
    assert dossier.migration_summary is None
