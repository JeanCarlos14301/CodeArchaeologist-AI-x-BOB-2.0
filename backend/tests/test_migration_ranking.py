"""Pruebas unitarias para el motor de recomendación de migración determinista (D3, D7).

Verifica:
1. Extracción y ranking determinista de las 10 rutas de FacturaYa.
2. Desglose matemático: valor, riesgo, testabilidad, puntaje.
3. Identificación de 'No empezar por aquí' (POST /invoices/new por alto riesgo/complejidad).
4. Olas del Strangler Fig y PERT heurístico no calibrado.
5. Análisis estático puro sin ejecución de código.
6. Ausencia de textos fijos heredados ('80% de los proyectos').
7. Exposición del endpoint GET /api/audits/{id}/migration.
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
    """Carga el dossier de referencia de FacturaYa si existe, o un dossier sintético completo."""
    if FIXTURE_DOSSIER.is_file():
        data = json.loads(FIXTURE_DOSSIER.read_text(encoding="utf-8"))
        return Dossier.model_validate(data)
    from app.contracts.schema_v1 import DossierStats
    findings = [
        Finding(
            id="F-1",
            title="Inyección SQL",
            category="security",
            subcategory="sql-injection",
            severity="critical",
            observed_or_inferred="observed",
            evidence=[{"path": "app.py", "line_start": 30, "line_end": 40, "snippet": "cursor.execute(query)"}],
            explanation="Concatenación directa de parámetros en SQL.",
            recommendation="Parametrizar las consultas con tuplas.",
        ),
        Finding(
            id="F-2",
            title="Lógica de negocio en controlador",
            category="architecture",
            subcategory="monolithic-coupling",
            severity="medium",
            observed_or_inferred="observed",
            evidence=[{"path": "app.py", "line_start": 80, "line_end": 120, "snippet": "def get_invoice"}],
            explanation="Cálculo de impuestos y subtotales acoplados a la ruta HTTP.",
            recommendation="Extraer a un servicio de dominio.",
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
    """Verifica que FacturaYa produce 10 candidatos ordenados deterministamente."""
    recommendation = analyze_route_candidates(
        workspace=FACTURAYA_DIR,
        dossier=facturaya_dossier,
    )

    assert isinstance(recommendation, MigrationRecommendation)
    assert len(recommendation.candidates) == 10

    # Verificar que están ordenados descendentemente por score
    scores = [c.score for c in recommendation.candidates]
    assert scores == sorted(scores, reverse=True)

    # Cada candidato tiene contrato completo y justificación no vacía
    for c in recommendation.candidates:
        assert c.rule.startswith("/")
        assert len(c.http_methods) > 0
        assert c.function_name
        assert c.value >= 1.0
        assert c.risk >= 1.0
        assert c.testability in (1.0, 0.5, 0.25)
        # score = round((valor * testability) / riesgo, 3)
        expected_score = round((c.value * c.testability) / c.risk, 3)
        assert c.score == expected_score
        assert len(c.why) > 10

    # El candidato recomendado tiene puntuación positiva y justificación
    assert recommendation.recommended is not None
    assert recommendation.recommended.rule
    assert recommendation.recommended.score > 0

    # Las alternativas contienen opciones viables
    assert len(recommendation.alternatives) in (1, 2)
    assert all(a.score > 0 for a in recommendation.alternatives)

    # 'No empezar por aquí' es la ruta más riesgosa
    no_start = recommendation.do_not_start_here
    assert no_start is not None
    assert no_start.rule in ("/invoices/new", "/invoices") or "new" in no_start.function_name
    assert no_start.risk > 15.0, "La ruta de mayor riesgo debe tener un riesgo compuesto significativo"
    assert "invoices" in no_start.tables_written or "invoice_items" in no_start.tables_written
    assert no_start.complexity > 20 or no_start.lines > 100


def test_wave_planning_and_pert_heuristics(facturaya_dossier: Dossier) -> None:
    """Verifica que las olas del Strangler Fig y el PERT cumplen la especificación."""
    recommendation = analyze_route_candidates(
        workspace=FACTURAYA_DIR,
        dossier=facturaya_dossier,
    )

    # Debe haber 3 olas
    assert len(recommendation.waves) == 3
    assert "Ola 1" in recommendation.waves[0].name
    assert "Ola 2" in recommendation.waves[1].name
    assert "Ola 3" in recommendation.waves[2].name

    # Todas las 10 rutas deben estar distribuidas entre las 3 olas sin duplicación
    all_wave_rules = []
    for w in recommendation.waves:
        all_wave_rules.extend([c.rule for c in w.candidates])
        # Cada ola tiene PERT con el disclaimer obligatorio
        assert isinstance(w.pert, PertEstimate)
        assert w.pert.expected_days > 0
        assert w.pert.optimistic_days <= w.pert.most_likely_days <= w.pert.pessimistic_days
        assert any(PERT_DISCLAIMER in a for a in w.pert.assumptions)

    assert len(all_wave_rules) == 10
    assert len(set(all_wave_rules)) == 10

    # El PERT del primer corte recomendado también incluye el disclaimer
    assert recommendation.first_cut_pert is not None
    assert recommendation.first_cut_pert.expected_days > 0
    assert any(PERT_DISCLAIMER in a for a in recommendation.first_cut_pert.assumptions)


def test_pert_formula_calculation() -> None:
    """Valida la fórmula de tres puntos O, M, P y desviación estándar en calculate_pert_for_scope."""
    pert = calculate_pert_for_scope(
        affected_routes=1,
        affected_functions=2,
        affected_lines=50,
        affected_complexity=10,
        scope_description="Ruta de prueba",
    )
    assert pert.optimistic_days <= pert.most_likely_days <= pert.pessimistic_days
    # expected_days = round((O + 4M + P)/6, 2)
    expected = (pert.optimistic_days + 4 * pert.most_likely_days + pert.pessimistic_days) / 6
    assert abs(pert.expected_days - expected) < 0.05
    assert pert.variance >= 0
    assert any(PERT_DISCLAIMER in a for a in pert.assumptions)


def test_static_analysis_never_executes_code(tmp_path: Path) -> None:
    """Verifica que el análisis estático NUNCA importa ni ejecuta el código del repositorio."""
    malicious_code = '''
# Si este código se importa o ejecuta, lanzará una excepción
raise RuntimeError("FATAL: Código de usuario fue ejecutado en el servidor!")

from flask import Flask
app = Flask(__name__)

@app.route("/api/test", methods=["GET"])
def test_endpoint():
    return {"status": "ok"}
'''
    target_file = tmp_path / "app.py"
    target_file.write_text(malicious_code, encoding="utf-8")

    # El análisis de ranking debe correr sobre tmp_path sin lanzar RuntimeError
    rec = analyze_route_candidates(
        workspace=tmp_path,
        dossier=None,
    )
    assert len(rec.candidates) == 1
    assert rec.candidates[0].rule == "/api/test"
    assert rec.candidates[0].function_name == "test_endpoint"


def test_no_legacy_hardcoded_strings_in_backend() -> None:
    """Garantiza que no quedan textos simulados ('80% de los proyectos') ni archivos obsoletos."""
    backend_app = REPO_ROOT / "backend" / "app"

    # Archivos borrados que NUNCA deben existir
    deleted_files = ["worker.py", "api/jobs.py", "api/migrate.py", "api/artifacts.py"]
    for rel_path in deleted_files:
        assert not (backend_app / rel_path).exists(), f"El archivo legado {rel_path} no debe existir"

    # Búsqueda de strings simuladas en todo backend/app
    forbidden_terms = [
        "80% de los proyectos",
        "plan_architecture_stage_4",
        "generate_narrative_stage_10",
        "audit_evidence_stage_2",
    ]
    for py_file in backend_app.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="replace")
        for term in forbidden_terms:
            assert term not in content, f"Encontrado término prohibido '{term}' en {py_file.name}"


def test_migration_api_endpoint_structure(tmp_path: Path) -> None:
    """Valida la respuesta del endpoint GET /api/audits/{id}/migration."""
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

        # Campos nuevos
        assert "recommendation" in data
        assert "candidates" in data
        assert len(data["candidates"]) == 10
        assert "recommended" in data
        assert "alternatives" in data
        assert "do_not_start_here" in data
        assert "waves" in data
        assert len(data["waves"]) == 3
        assert "first_cut_pert" in data

        # Compatibilidad con frontend previo
        assert "result" in data
        assert "legacy_code" in data
        assert "modern_code" in data
        assert "facade_code" in data
