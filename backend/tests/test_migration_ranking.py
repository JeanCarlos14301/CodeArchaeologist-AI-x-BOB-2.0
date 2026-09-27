"""Unit tests for the deterministic migration recommendation engine (D3, D7).

Checks:
1. Deterministic extraction and ranking of FacturaYa's 10 routes.
2. Mathematical breakdown: value, risk, testability, score.
3. Identification of 'do not start here' (POST /invoices/new because of high risk/complexity).
4. Strangler Fig waves and the uncalibrated heuristic PERT.
5. Pure static analysis with no code execution.
6. No leftover hardcoded texts ('80% of projects').
7. Exposure of the GET /api/audits/{id}/migration endpoint.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.contracts.schema_v1 import (
    Dossier,
    Finding,
    MigrationRecommendation,
    PertEstimate,
    RouteCandidate,
)
from app.pipeline.migration_ranking import (
    PERT_DISCLAIMER,
    analyze_route_candidates,
    calculate_pert_for_scope,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FACTURAYA_DIR = REPO_ROOT / "samples" / "facturaya-v1"
FIXTURE_DOSSIER = REPO_ROOT / "contracts" / "fixtures" / "dossier-example.json"


@pytest.fixture
def facturaya_dossier() -> Dossier:
    """Loads FacturaYa's reference dossier if it exists, or a complete synthetic dossier."""
    if FIXTURE_DOSSIER.is_file():
        data = json.loads(FIXTURE_DOSSIER.read_text(encoding="utf-8"))
        return Dossier.model_validate(data)
    from app.contracts.schema_v1 import DossierStats
    findings = [
        Finding(
            id="F-1",
            title="SQL injection",
            category="security",
            subcategory="sql-injection",
            severity="critical",
            observed_or_inferred="observed",
            evidence=[{"path": "app.py", "line_start": 30, "line_end": 40, "snippet": "cursor.execute(query)"}],
            explanation="Direct concatenation of parameters into SQL.",
            recommendation="Parameterize the queries with tuples.",
        ),
        Finding(
            id="F-2",
            title="Business logic in the controller",
            category="architecture",
            subcategory="monolithic-coupling",
            severity="medium",
            observed_or_inferred="observed",
            evidence=[{"path": "app.py", "line_start": 80, "line_end": 120, "snippet": "def get_invoice"}],
            explanation="Tax and subtotal calculations coupled to the HTTP route.",
            recommendation="Extract into a domain service.",
        ),
    ]
    return Dossier(
        execution_mode="example",
        repo_name="facturaya-v1",
        generated_at="2026-09-26T12:00:00Z",
        job_id="test-job",
        findings=findings,
        evidence_checks=[],
        stats=DossierStats(
            findings_reported=len(findings),
            findings_validated=len(findings),
            evidence_total=len(findings),
            evidence_valid=len(findings),
            evidence_valid_ratio=1.0,
        ),
    )


def test_facturaya_candidates_ranking(facturaya_dossier: Dossier) -> None:
    """Checks that FacturaYa produces 10 deterministically ordered candidates."""
    recommendation = analyze_route_candidates(
        workspace=FACTURAYA_DIR,
        dossier=facturaya_dossier,
    )

    assert isinstance(recommendation, MigrationRecommendation)
    assert len(recommendation.candidates) == 10

    # Check they are sorted by score, descending
    scores = [c.score for c in recommendation.candidates]
    assert scores == sorted(scores, reverse=True)

    # Each candidate has a complete contract and a non-empty justification
    for c in recommendation.candidates:
        assert c.rule.startswith("/")
        assert len(c.http_methods) > 0
        assert c.function_name
        assert c.value >= 1.0
        assert c.risk >= 1.0
        assert c.testability in (1.0, 0.5, 0.25)
        # score = round((value * testability * business data) / risk, 3)
        business_factor = 1.0 if c.touches_business_data else 0.5
        expected_score = round((c.value * c.testability * business_factor) / c.risk, 3)
        assert c.score == expected_score
        assert len(c.why) > 10

    # The recommended candidate has a positive score and a justification
    assert recommendation.recommended is not None
    assert recommendation.recommended.rule
    assert recommendation.recommended.score > 0

    # The alternatives contain viable options
    assert len(recommendation.alternatives) in (1, 2)
    assert all(a.score > 0 for a in recommendation.alternatives)

    # 'Do not start here' is the riskiest route
    no_start = recommendation.do_not_start_here
    assert no_start is not None
    assert no_start.rule in ("/invoices/new", "/invoices") or "new" in no_start.function_name
    assert no_start.risk > 15.0, "The highest-risk route must have a significant composite risk"
    assert "invoices" in no_start.tables_written or "invoice_items" in no_start.tables_written
    assert no_start.complexity > 20 or no_start.lines > 100


def test_wave_planning_and_pert_heuristics(facturaya_dossier: Dossier) -> None:
    """Checks that the Strangler Fig waves and the PERT meet the specification."""
    recommendation = analyze_route_candidates(
        workspace=FACTURAYA_DIR,
        dossier=facturaya_dossier,
    )

    # There must be 3 waves
    assert len(recommendation.waves) == 3
    assert "Wave 1" in recommendation.waves[0].name
    assert "Wave 2" in recommendation.waves[1].name
    assert "Wave 3" in recommendation.waves[2].name

    # All 10 routes must be spread across the 3 waves without duplication
    all_wave_rules = []
    for w in recommendation.waves:
        all_wave_rules.extend([c.rule for c in w.candidates])
        # Each wave has a PERT with the mandatory disclaimer
        assert isinstance(w.pert, PertEstimate)
        assert w.pert.expected_days > 0
        assert w.pert.optimistic_days <= w.pert.most_likely_days <= w.pert.pessimistic_days
        assert any(PERT_DISCLAIMER in a for a in w.pert.assumptions)

    assert len(all_wave_rules) == 10
    assert len(set(all_wave_rules)) == 10

    # The PERT of the recommended first cut also includes the disclaimer
    assert recommendation.first_cut_pert is not None
    assert recommendation.first_cut_pert.expected_days > 0
    assert any(PERT_DISCLAIMER in a for a in recommendation.first_cut_pert.assumptions)


def test_pert_formula_calculation() -> None:
    """Validates the three-point formula O, M, P and the standard deviation in calculate_pert_for_scope."""
    pert = calculate_pert_for_scope(
        affected_routes=1,
        affected_functions=2,
        affected_lines=50,
        affected_complexity=10,
        scope_description="Test route",
    )
    assert pert.optimistic_days <= pert.most_likely_days <= pert.pessimistic_days
    # expected_days = round((O + 4M + P)/6, 2)
    expected = (pert.optimistic_days + 4 * pert.most_likely_days + pert.pessimistic_days) / 6
    assert abs(pert.expected_days - expected) < 0.05
    assert pert.variance >= 0
    assert any(PERT_DISCLAIMER in a for a in pert.assumptions)


def test_static_analysis_never_executes_code(tmp_path: Path) -> None:
    """Checks that the static analysis NEVER imports or runs the repository's code."""
    malicious_code = '''
# If this code is imported or run, it raises an exception
raise RuntimeError("FATAL: user code was executed on the server!")

from flask import Flask
app = Flask(__name__)

@app.route("/api/test", methods=["GET"])
def test_endpoint():
    return {"status": "ok"}
'''
    target_file = tmp_path / "app.py"
    target_file.write_text(malicious_code, encoding="utf-8")

    # The ranking analysis must run on tmp_path without raising RuntimeError
    rec = analyze_route_candidates(
        workspace=tmp_path,
        dossier=None,
    )
    assert len(rec.candidates) == 1
    assert rec.candidates[0].rule == "/api/test"
    assert rec.candidates[0].function_name == "test_endpoint"


def test_no_legacy_hardcoded_strings_in_backend() -> None:
    """Guarantees there are no simulated texts ('80% of projects') or obsolete files left."""
    backend_app = REPO_ROOT / "backend" / "app"

    # Deleted files that must NEVER exist
    deleted_files = ["worker.py", "api/jobs.py", "api/migrate.py", "api/artifacts.py"]
    for rel_path in deleted_files:
        assert not (backend_app / rel_path).exists(), f"The legacy file {rel_path} must not exist"

    # Search for simulated strings across backend/app
    forbidden_terms = [
        "80% de los proyectos",
        "80% of projects",
        "plan_architecture_stage_4",
        "generate_narrative_stage_10",
        "audit_evidence_stage_2",
    ]
    for py_file in backend_app.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="replace")
        for term in forbidden_terms:
            assert term not in content, f"Found forbidden term '{term}' in {py_file.name}"


def test_migration_api_endpoint_structure(tmp_path: Path) -> None:
    """Validates the response of the GET /api/audits/{id}/migration endpoint."""
    from app.main import create_app

    artifacts_dir = tmp_path / "artifacts"
    app = create_app(artifacts_dir=artifacts_dir, frontend_dist=tmp_path / "no-dist")
    with TestClient(app) as client:
        res = client.post("/api/audits", json={"sample": "facturaya-v1", "execution_mode": "imported"})
        assert res.status_code in (200, 202)
        job_id = res.json()["id"]

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            poll = client.get(f"/api/audits/{job_id}").json()
            if poll["job"]["status"] in ("done", "failed"):
                break
            time.sleep(0.05)

        response = client.get(f"/api/audits/{job_id}/migration")
        assert response.status_code == 200
        data = response.json()

        # New fields
        assert "recommendation" in data
        assert "candidates" in data
        assert len(data["candidates"]) == 10
        assert "recommended" in data
        assert "alternatives" in data
        assert "do_not_start_here" in data
        assert "waves" in data
        assert len(data["waves"]) == 3
        assert "first_cut_pert" in data

        # Compatibility with the previous frontend
        assert "result" in data
        assert "legacy_code" in data
        assert "modern_code" in data
        assert "facade_code" in data


def test_first_cut_is_a_business_route_not_a_trivial_one(facturaya_dossier: Dossier) -> None:
    """Regression: a 4-line POST /logout holding a cross-cutting CSRF finding used to win the ranking."""
    recommendation = analyze_route_candidates(workspace=FACTURAYA_DIR, dossier=facturaya_dossier)

    assert recommendation.recommended is not None
    assert recommendation.recommended.touches_business_data
    assert "logout" not in recommendation.recommended.rule
    logout = next(c for c in recommendation.candidates if c.rule == "/logout")
    assert not logout.touches_business_data and "business data" in logout.why
