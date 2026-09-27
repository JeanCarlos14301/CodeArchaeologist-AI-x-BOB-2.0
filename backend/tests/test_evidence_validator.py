"""Tests for the deterministic validator of physical evidence in code (D-06)."""

from pathlib import Path
import pytest

from backend.app.models import EvidenceLocation, Finding
from backend.app.validators.evidence_validator import (
    validate_dossier_evidence,
    validate_evidence_location,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_real_evidence_validation_on_facturaya():
    """Checks that the real citations on FacturaYa v1 reach 100% fidelity."""
    sample_dir = BASE_DIR / "samples" / "facturaya-v1"
    if not sample_dir.exists():
        pytest.skip("samples/facturaya-v1 directory is unavailable")

    findings = [
        Finding(
            id="EF-1",
            title="SQL injection",
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
            explanation="Direct concatenation of the q parameter.",
            verification_method="Test SQL injection.",
            blast_radius_score=85.0,
        ),
        Finding(
            id="EF-4",
            title="Secret in code",
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
            explanation="Hardcoded secret key.",
            verification_method="Static inspection.",
            blast_radius_score=40.0,
        ),
    ]

    validated, report = validate_dossier_evidence(sample_dir, findings)
    assert report.fidelity_ratio == 1.0
    assert report.valid_references == 2
    assert report.invalid_references == 0
    assert all(f.status == "accepted" for f in validated)


def test_hallucinated_evidence_is_detected_and_rejected():
    """Checks that a fictitious citation produced by an LLM hallucination is detected and rejected."""
    sample_dir = BASE_DIR / "samples" / "facturaya-v1"
    if not sample_dir.exists():
        pytest.skip("samples/facturaya-v1 directory is unavailable")

    fake_findings = [
        Finding(
            id="HALLUCINATED-1",
            title="Phantom vulnerability in a missing file",
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
            explanation="Typical LLM hallucination.",
            verification_method="N/A",
            blast_radius_score=10.0,
        ),
        Finding(
            id="HALLUCINATED-2",
            title="Citation with out-of-range lines in a real file",
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
            explanation="Lines that do not exist in config.py.",
            verification_method="N/A",
            blast_radius_score=10.0,
        ),
    ]

    validated, report = validate_dossier_evidence(sample_dir, fake_findings)
    assert report.valid_references == 0
    assert report.invalid_references == 2
    assert report.fidelity_ratio == 0.0
    assert all(f.status in ["rejected", "inferred"] for f in validated)
