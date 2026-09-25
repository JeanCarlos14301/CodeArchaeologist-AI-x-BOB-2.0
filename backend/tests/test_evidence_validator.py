"""Pruebas del Validador Determinista de Evidencia Física en Código (D-06)."""

from pathlib import Path
import pytest

from backend.app.models import EvidenceLocation, Finding
from backend.app.validators.evidence_validator import (
    validate_dossier_evidence,
    validate_evidence_location,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_real_evidence_validation_on_facturaya():
    """Verifica que las citas reales sobre FacturaYa v1 obtengan 100% de fidelidad."""
    sample_dir = BASE_DIR / "samples" / "facturaya-v1"
    if not sample_dir.exists():
        pytest.skip("Directorio samples/facturaya-v1 no disponible")

    findings = [
        Finding(
            id="EF-1",
            title="Inyección SQL",
            category="security/sql-injection",
            severity="CRITICAL",
            confidence="HIGH",
            priority="P0",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="app.py",
                    line_start=78,
                    line_end=78,
                    fragment='sql = "SELECT id, number, issue_date, total FROM invoices WHERE owner_id = "',
                    observed_or_inferred="observed",
                )
            ],
            explanation="Concatenación directa de parámetro q.",
            verification_method="Test SQL injection.",
            blast_radius_score=85.0,
        ),
        Finding(
            id="EF-4",
            title="Secreto en código",
            category="security/hardcoded-secret",
            severity="HIGH",
            confidence="HIGH",
            priority="P1",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="config.py",
                    line_start=3,
                    line_end=3,
                    fragment='SECRET_KEY = "DEMO_ONLY_NOT_A_REAL_SECRET"',
                    observed_or_inferred="observed",
                )
            ],
            explanation="Secret key hardcodeada.",
            verification_method="Inspección estática.",
            blast_radius_score=40.0,
        ),
    ]

    validated, report = validate_dossier_evidence(sample_dir, findings)
    assert report.fidelity_ratio == 1.0
    assert report.valid_references == 2
    assert report.invalid_references == 0
    assert all(f.status == "accepted" for f in validated)


def test_hallucinated_evidence_is_detected_and_rejected():
    """Verifica que una cita ficticia generada por alucinación de un LLM sea detectada y rechazada."""
    sample_dir = BASE_DIR / "samples" / "facturaya-v1"
    if not sample_dir.exists():
        pytest.skip("Directorio samples/facturaya-v1 no disponible")

    fake_findings = [
        Finding(
            id="HALLUCINATED-1",
            title="Vulnerabilidad fantasma en archivo inexistente",
            category="security/fake",
            severity="CRITICAL",
            confidence="HIGH",
            priority="P0",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="non_existent_module.py",
                    line_start=10,
                    line_end=15,
                    fragment="def nonexistent_danger(): pass",
                    observed_or_inferred="observed",
                )
            ],
            explanation="Alucinación típica de LLM.",
            verification_method="N/A",
            blast_radius_score=10.0,
        ),
        Finding(
            id="HALLUCINATED-2",
            title="Cita con líneas fuera de rango en archivo real",
            category="security/fake-lines",
            severity="HIGH",
            confidence="HIGH",
            priority="P1",
            expected_detection=True,
            evidence=[
                EvidenceLocation(
                    path="config.py",
                    line_start=9999,
                    line_end=10005,
                    fragment="MAGIC_SECRET_NOT_THERE = 1",
                    observed_or_inferred="observed",
                )
            ],
            explanation="Líneas inexistentes en config.py.",
            verification_method="N/A",
            blast_radius_score=10.0,
        ),
    ]

    validated, report = validate_dossier_evidence(sample_dir, fake_findings)
    assert report.valid_references == 0
    assert report.invalid_references == 2
    assert report.fidelity_ratio == 0.0
    assert all(f.status in ["rejected", "inferred"] for f in validated)
