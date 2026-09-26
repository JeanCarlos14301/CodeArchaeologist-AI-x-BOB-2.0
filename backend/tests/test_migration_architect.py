"""Tests deterministas para la etapa migration-architect (opciones sobre el ranking de rutas).

No invocan Bob live: usan un stub de BobAdapter que devuelve respuestas fijas.
Cubren: respuesta válida, endpoint o hallazgo inventado, cifras en pros/cons, recomendación
distinta del corte del motor, JSON inválido, fallo de Bob, ranking vacío y topes de la sesión.
"""

import json
from unittest.mock import MagicMock

from app.adapters.bob_adapter import BobExecutionError, BobResult, BobStats
from app.contracts.schema_v1 import (
    Dossier,
    DossierStats,
    Evidence,
    Finding,
    MigrationRecommendation,
    RouteCandidate,
)
from app.pipeline.migration_architect import (
    ARCHITECT_MAX_COST,
    architect_settings,
    run_migration_architect,
)

RECOMMENDED = "GET /invoices/<int:invoice_id>"
ALT_1 = "GET /customers"
ALT_2 = "GET /reports/monthly"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stub_adapter(last_message: str, fail: bool = False) -> MagicMock:
    """Crea un BobAdapter stub cuyo .run() devuelve last_message o lanza BobExecutionError."""
    adapter = MagicMock()
    if fail:
        adapter.run.side_effect = BobExecutionError("Bob simulado falló")
    else:
        adapter.run.return_value = BobResult(
            mode="migration-architect",
            status="success",
            last_message=last_message,
            stats=BobStats(task_id="t-test", duration_ms=100, session_costs=0.01),
            execution_mode="live",
        )
    return adapter


def _candidate(endpoint: str, score: float, findings: list[str]) -> RouteCandidate:
    method, rule = endpoint.split(" ", 1)
    return RouteCandidate(
        endpoint=endpoint, http_methods=[method], rule=rule, function_name=rule.strip("/").replace("/", "_") or "index",
        file_path="app.py", line_start=1, line_end=10, value=1.0 + len(findings), risk=2.0, testability=1.0,
        score=score, formula="calculada", findings_mitigated=findings, why="Responde JSON puro con contrato formal.",
    )


def _dossier(with_routes: bool = True) -> Dossier:
    findings = [
        Finding(
            id=fid,
            title=f"Hallazgo {fid}",
            category="security",
            subcategory="test",
            severity="high",
            observed_or_inferred="observed",
            evidence=[Evidence(path="app.py", line_start=1, line_end=2, snippet="x = 1")],
            explanation="Descripción de prueba suficientemente larga.",
            recommendation="Corregir.",
        )
        for fid in ("F-1", "F-2", "F-3")
    ]
    recommendation = None
    if with_routes:
        recommended = _candidate(RECOMMENDED, 2.0, ["F-2"])
        alternatives = [_candidate(ALT_1, 1.0, []), _candidate(ALT_2, 0.5, ["F-3"])]
        recommendation = MigrationRecommendation(
            recommended=recommended, alternatives=alternatives, candidates=[recommended, *alternatives],
        )
    return Dossier(
        execution_mode="live",
        repo_name="repo-test",
        generated_at="2026-01-01T00:00:00+00:00",
        findings=findings,
        evidence_checks=[],
        stats=DossierStats(
            findings_reported=3, findings_validated=3, evidence_total=3, evidence_valid=3, evidence_valid_ratio=1.0,
        ),
        recommendation=recommendation,
    )


def _valid_payload() -> dict:
    """Respuesta que pasa todos los validadores: una opción por candidato, la recomendada es la del motor."""
    return {"migration_options": [
        {
            "id": "OPT-1", "name": "Extraer primero el detalle de factura", "pattern": "Strangler Fig",
            "endpoint": RECOMMENDED, "finding_ids": ["F-2"],
            "pros": ["Contrato JSON fácil de fijar con pruebas", "Rollback sencillo detrás de la fachada"],
            "cons": ["Exige mantener la fachada temporal"], "recommended": True,
        },
        {
            "id": "OPT-2", "name": "Empezar por el listado de clientes", "pattern": "Strangler Fig",
            "endpoint": ALT_1, "finding_ids": [],
            "pros": ["Ruta de solo lectura"], "cons": ["Aporta poco valor de negocio al inicio"], "recommended": False,
        },
        {
            "id": "OPT-3", "name": "Empezar por el reporte mensual", "pattern": "Strangler Fig",
            "endpoint": ALT_2, "finding_ids": ["F-3"],
            "pros": ["Aísla una regla de descuento"], "cons": ["Depende de consultas agregadas"], "recommended": False,
        },
    ]}


def _run(payload: dict | str, dossier: Dossier | None = None) -> tuple[list, str]:
    message = payload if isinstance(payload, str) else json.dumps(payload)
    return run_migration_architect(dossier or _dossier(), _stub_adapter(message))


# ---------------------------------------------------------------------------
# Casos de prueba
# ---------------------------------------------------------------------------

def test_valid_response_returns_one_option_per_candidate_in_ranking_order() -> None:
    options, reason = _run(_valid_payload())

    assert reason == ""
    assert [option.endpoint for option in options] == [RECOMMENDED, ALT_1, ALT_2]
    assert [option.recommended for option in options] == [True, False, False]


def test_prompt_carries_the_route_ranking_not_the_finding_ranking() -> None:
    adapter = _stub_adapter(json.dumps(_valid_payload()))
    run_migration_architect(_dossier(), adapter)

    prompt = adapter.run.call_args.args[1]
    assert RECOMMENDED in prompt and ALT_1 in prompt and ALT_2 in prompt
    assert "risk_matrix" not in prompt


def test_endpoint_not_in_ranking_is_rejected() -> None:
    payload = _valid_payload()
    payload["migration_options"][1]["endpoint"] = "GET /inventada"

    options, reason = _run(payload)

    assert options == [] and "/inventada" in reason


def test_duplicated_endpoint_is_rejected() -> None:
    payload = _valid_payload()
    payload["migration_options"][2]["endpoint"] = ALT_1

    options, reason = _run(payload)

    assert options == [] and "mismo endpoint" in reason


def test_finding_not_mitigated_by_that_candidate_is_rejected() -> None:
    payload = _valid_payload()
    payload["migration_options"][1]["finding_ids"] = ["F-1"]  # GET /customers no mitiga F-1

    options, reason = _run(payload)

    assert options == [] and "F-1" in reason


def test_number_in_pros_is_rejected() -> None:
    payload = _valid_payload()
    payload["migration_options"][0]["pros"][0] = "Reduce riesgo en un 80%"

    options, reason = _run(payload)

    assert options == [] and "cifras" in reason


def test_estimate_written_in_words_is_rejected() -> None:
    payload = _valid_payload()
    payload["migration_options"][0]["pros"] = ["Se entrega en dos semanas"]

    options, reason = _run(payload)

    assert options == [] and "cifras" in reason


def test_two_recommended_is_rejected() -> None:
    payload = _valid_payload()
    payload["migration_options"][1]["recommended"] = True

    options, reason = _run(payload)

    assert options == [] and "recomendada" in reason


def test_recommending_other_than_the_engine_cut_is_rejected() -> None:
    """Bob explica el corte del motor (D3); no puede recomendar otro."""
    payload = _valid_payload()
    payload["migration_options"][0]["recommended"] = False
    payload["migration_options"][2]["recommended"] = True

    options, reason = _run(payload)

    assert options == [] and "no es el corte que eligió el motor" in reason


def test_wrong_option_count_is_rejected() -> None:
    payload = _valid_payload()
    payload["migration_options"] = payload["migration_options"][:2]

    options, reason = _run(payload)

    assert options == [] and "exactamente 3" in reason


def test_invalid_json_is_rejected() -> None:
    options, reason = _run("Esto no es JSON en absoluto.")

    assert options == [] and reason != ""


def test_bob_failure_produces_empty_fallback() -> None:
    options, reason = run_migration_architect(_dossier(), _stub_adapter("", fail=True))

    assert options == [] and "migration-architect" in reason


def test_no_route_candidates_short_circuits_without_calling_bob() -> None:
    adapter = _stub_adapter("")

    options, reason = run_migration_architect(_dossier(with_routes=False), adapter)

    adapter.run.assert_not_called()
    assert options == [] and reason != ""


def test_architect_session_is_bounded() -> None:
    settings = architect_settings()

    assert settings.max_cost <= ARCHITECT_MAX_COST
    assert settings.disable_subagents and settings.disable_mcp
    assert settings.max_turns <= 6


def test_imported_audit_never_calls_bob_and_still_completes(tmp_path) -> None:
    """Regresión: la etapa nueva rompía cada auditoría (etapa fuera del vocabulario) y llamaba a Bob al importar."""
    from pathlib import Path

    from app.pipeline.activity import EventLog
    from app.pipeline.evidence_audit import run_evidence_audit

    root = Path(__file__).resolve().parents[2]
    adapter = MagicMock()
    stages: list[str] = []
    dossier = run_evidence_audit(
        root / "samples" / "facturaya-v1",
        tmp_path,
        adapter=adapter,
        imported_result=root / "contracts" / "fixtures" / "bob-evidence-auditor-facturaya.json",
        on_stage=stages.append,
        events=EventLog(tmp_path / "events.jsonl"),
    )
    adapter.run.assert_not_called()
    assert dossier.migration_options == []
    assert stages == ["preparing", "auditing", "validating", "migration"]
    # La recomendación y su PERT se calculan igual en modo importado.
    assert dossier.recommendation is not None and dossier.recommendation.recommended is not None
    assert dossier.first_cut_pert == dossier.recommendation.first_cut_pert
