"""Riesgo y esfuerzo deben depender del código medido, no de cifras fijas."""

from pathlib import Path

from app.contracts.schema_v1 import Dossier, DossierStats, Evidence, Finding
from app.pipeline.decision_metrics import calculate_decision_metrics


def _dossier() -> Dossier:
    return Dossier(
        execution_mode="imported",
        repo_name="repo",
        generated_at="2026-09-25T13:50:00-05:00",
        findings=[Finding(
            id="F-1", title="Riesgo medido", category="security", subcategory="test",
            severity="high", observed_or_inferred="observed",
            evidence=[Evidence(path="app.py", line_start=2, line_end=3, snippet="def target():")],
            explanation="Hallazgo de prueba con evidencia suficiente.", recommendation="Corregir y probar.",
        )],
        evidence_checks=[],
        stats=DossierStats(
            findings_reported=1, findings_validated=1, evidence_total=1,
            evidence_valid=1, evidence_valid_ratio=1.0,
        ),
    )


def test_two_repositories_produce_different_risk_and_pert(tmp_path: Path) -> None:
    small = tmp_path / "small"
    large = tmp_path / "large"
    small.mkdir()
    large.mkdir()
    (small / "app.py").write_text("\ndef target():\n    return 1\n", encoding="utf-8")
    (large / "app.py").write_text(
        "\ndef target():\n    return 1\n\ndef caller():\n    return target()\n"
        "\ndef route():\n    return caller()\n",
        encoding="utf-8",
    )

    small_risk, small_pert = calculate_decision_metrics(small, _dossier())
    large_risk, large_pert = calculate_decision_metrics(large, _dossier())

    assert small_risk[0].score < large_risk[0].score
    assert small_pert is not None and large_pert is not None
    assert small_pert.expected_days < large_pert.expected_days
    assert "rutas" in large_pert.formula and "complejidad" in large_pert.formula
    assert large_pert.assumptions
