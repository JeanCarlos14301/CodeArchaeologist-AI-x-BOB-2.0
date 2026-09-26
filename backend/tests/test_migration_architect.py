"""Tests deterministas para la etapa migration-architect.

No invocan Bob live: usan un stub de BobAdapter que devuelve respuestas fijas.
Cubren: respuesta válida, finding_id inventado, cifra en pros/cons,
dos opciones recomendadas, y JSON inválido.
"""

import json
from unittest.mock import MagicMock

import pytest

from app.adapters.bob_adapter import BobExecutionError, BobResult, BobStats
from app.contracts.schema_v1 import (
    Dossier,
    DossierStats,
    Evidence,
    Finding,
    MigrationOption,
    RiskMetric,
)
from app.pipeline.migration_architect import (
    _extract_options,
    _validate_options,
    run_migration_architect,
)


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


def _dossier_with_risk(scores: list[tuple[str, int, str]]) -> Dossier:
    """Crea un Dossier mínimo con los hallazgos y risk_matrix dados.

    scores: lista de (finding_id, score, severity)
    """
    findings = [
        Finding(
            id=fid,
            title=f"Hallazgo {fid}",
            category="security",
            subcategory="test",
            severity=sev,
            observed_or_inferred="observed",
            evidence=[Evidence(path="app.py", line_start=1, line_end=2, snippet="x = 1")],
            explanation="Descripción de prueba suficientemente larga.",
            recommendation="Corregir.",
        )
        for fid, _score, sev in scores
    ]
    risk_matrix = [
        RiskMetric(
            finding_id=fid,
            severity_weight={"critical": 4, "high": 3, "medium": 2, "low": 1}[sev],
            origin_functions=1,
            impacted_callers=score - {"critical": 4, "high": 3, "medium": 2, "low": 1}[sev],
            score=score,
            formula=f"{score}",
        )
        for fid, score, sev in scores
    ]
    return Dossier(
        execution_mode="imported",
        repo_name="repo-test",
        generated_at="2026-01-01T00:00:00+00:00",
        findings=findings,
        evidence_checks=[],
        stats=DossierStats(
            findings_reported=len(findings),
            findings_validated=len(findings),
            evidence_total=len(findings),
            evidence_valid=len(findings),
            evidence_valid_ratio=1.0,
        ),
        risk_matrix=risk_matrix,
    )


def _valid_response(top_id: str, other_ids: list[str]) -> str:
    """Construye una respuesta JSON válida que pasa todos los validadores."""
    all_ids = [top_id, *other_ids]
    options = [
        {
            "id": "OPT-1",
            "name": "Strangler Fig incremental por endpoint",
            "pattern": "Strangler Fig",
            "finding_ids": [top_id],
            "pros": ["Bajo riesgo operativo", "Rollback sencillo sin tiempo de inactividad"],
            "cons": ["Requiere mantener fachada temporal", "Coexistencia transitoria de dos stacks"],
            "recommended": True,
        },
        {
            "id": "OPT-2",
            "name": "Reescritura completa del módulo crítico",
            "pattern": "Big Bang parcial",
            "finding_ids": [all_ids[1]] if len(all_ids) > 1 else [top_id],
            "pros": ["Elimina deuda técnica de raíz"],
            "cons": ["Alto riesgo de regresión", "Periodo largo sin entregas"],
            "recommended": False,
        },
        {
            "id": "OPT-3",
            "name": "Extracción del núcleo transaccional",
            "pattern": "Core Domain Extraction",
            "finding_ids": [all_ids[-1]],
            "pros": ["Ataca directamente la complejidad del dominio"],
            "cons": ["Dependencias circulares dificultan el corte inicial"],
            "recommended": False,
        },
    ]
    return json.dumps({"migration_options": options})


# ---------------------------------------------------------------------------
# Casos de prueba
# ---------------------------------------------------------------------------

def test_valid_response_returns_three_options() -> None:
    """Respuesta bien formada: se devuelven exactamente 3 opciones y la primera es la recomendada."""
    dossier = _dossier_with_risk([("F-1", 12, "critical"), ("F-2", 6, "high"), ("F-3", 3, "medium")])
    response = _valid_response("F-1", ["F-2", "F-3"])
    adapter = _stub_adapter(response)

    options, reason = run_migration_architect(dossier, adapter)

    assert reason == ""
    assert len(options) == 3
    recommended = [opt for opt in options if opt.recommended]
    assert len(recommended) == 1
    assert "F-1" in recommended[0].finding_ids


def test_invented_finding_id_is_rejected() -> None:
    """finding_id inexistente en el ranking produce rechazo con motivo."""
    dossier = _dossier_with_risk([("F-1", 12, "critical"), ("F-2", 6, "high"), ("F-3", 3, "medium")])
    # OPT-1 referencia F-99 que no existe en el ranking
    options_data = json.loads(_valid_response("F-1", ["F-2", "F-3"]))
    options_data["migration_options"][0]["finding_ids"] = ["F-99"]
    adapter = _stub_adapter(json.dumps(options_data))

    options, reason = run_migration_architect(dossier, adapter)

    assert options == []
    assert "F-99" in reason


def test_number_in_pros_is_rejected() -> None:
    """Cifra numérica en pros produce rechazo."""
    dossier = _dossier_with_risk([("F-1", 12, "critical"), ("F-2", 6, "high"), ("F-3", 3, "medium")])
    options_data = json.loads(_valid_response("F-1", ["F-2", "F-3"]))
    # Introduce un número prohibido
    options_data["migration_options"][0]["pros"][0] = "Reduce riesgo en un 80%"
    adapter = _stub_adapter(json.dumps(options_data))

    options, reason = run_migration_architect(dossier, adapter)

    assert options == []
    assert "cifras" in reason or "pros" in reason or "porcentajes" in reason


def test_two_recommended_is_rejected() -> None:
    """Dos opciones recomendadas produce rechazo."""
    dossier = _dossier_with_risk([("F-1", 12, "critical"), ("F-2", 6, "high"), ("F-3", 3, "medium")])
    options_data = json.loads(_valid_response("F-1", ["F-2", "F-3"]))
    options_data["migration_options"][1]["recommended"] = True  # segunda también recomendada
    adapter = _stub_adapter(json.dumps(options_data))

    options, reason = run_migration_architect(dossier, adapter)

    assert options == []
    assert "recomendada" in reason


def test_invalid_json_is_rejected() -> None:
    """Respuesta que no es JSON válido produce fallback vacío."""
    dossier = _dossier_with_risk([("F-1", 12, "critical"), ("F-2", 6, "high"), ("F-3", 3, "medium")])
    adapter = _stub_adapter("Esto no es JSON en absoluto.")

    options, reason = run_migration_architect(dossier, adapter)

    assert options == []
    assert reason != ""


def test_bob_failure_produces_empty_fallback() -> None:
    """Si Bob lanza BobExecutionError, migration_options queda vacío y se registra motivo."""
    dossier = _dossier_with_risk([("F-1", 12, "critical"), ("F-2", 6, "high"), ("F-3", 3, "medium")])
    adapter = _stub_adapter("", fail=True)

    options, reason = run_migration_architect(dossier, adapter)

    assert options == []
    assert "migration-architect" in reason


def test_empty_risk_matrix_short_circuits() -> None:
    """Sin risk_matrix no se llama a Bob y migration_options queda vacío."""
    dossier = _dossier_with_risk([])
    adapter = _stub_adapter("")

    options, reason = run_migration_architect(dossier, adapter)

    adapter.run.assert_not_called()
    assert options == []
    assert reason != ""


# ---------------------------------------------------------------------------
# Reglas añadidas en la revisión y contrato con el pipeline
# ---------------------------------------------------------------------------

def _three_ids() -> list[tuple[str, int, str]]:
    return [("F-1", 12, "critical"), ("F-2", 6, "high"), ("F-3", 3, "medium")]


def test_wrong_option_count_is_rejected() -> None:
    dossier = _dossier_with_risk(_three_ids())
    payload = json.loads(_valid_response("F-1", ["F-2", "F-3"]))
    payload["migration_options"] = payload["migration_options"][:2]

    options, reason = run_migration_architect(dossier, _stub_adapter(json.dumps(payload)))

    assert options == [] and "exactamente 3" in reason


def test_estimate_written_in_words_is_rejected() -> None:
    dossier = _dossier_with_risk(_three_ids())
    payload = json.loads(_valid_response("F-1", ["F-2", "F-3"]))
    payload["migration_options"][0]["pros"] = ["Se entrega en dos semanas"]

    options, reason = run_migration_architect(dossier, _stub_adapter(json.dumps(payload)))

    assert options == [] and "cifras" in reason


def test_tie_break_matches_decision_metrics() -> None:
    """Con el mismo score gana la mayor severidad, igual que el primer corte que calcula el código."""
    dossier = _dossier_with_risk([("F-1", 8, "high"), ("F-2", 8, "critical"), ("F-3", 1, "low")])
    # F-2 gana por severidad aunque F-1 tenga el id más bajo; la recomendada debe atacarlo.
    ok = json.loads(_valid_response("F-2", ["F-1", "F-3"]))
    options, reason = run_migration_architect(dossier, _stub_adapter(json.dumps(ok)))
    assert reason == "" and len(options) == 3


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
