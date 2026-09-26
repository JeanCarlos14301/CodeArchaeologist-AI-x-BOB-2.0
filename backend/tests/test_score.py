"""Pruebas de evaluation/score.py: reglas de acierto, rechazados y falsos positivos."""

import importlib.util
import json
from pathlib import Path

import pytest

from app.adapters.bob_adapter import BobAdapter
from app.pipeline.evidence_audit import AUDITOR_MODE, build_dossier

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "samples" / "facturaya-v1"
RECORDED_BOB = REPO_ROOT / "contracts" / "fixtures" / "bob-evidence-auditor-facturaya.json"
EXPECTED = REPO_ROOT / "evaluation" / "expected-findings.json"

_spec = importlib.util.spec_from_file_location("score", REPO_ROOT / "evaluation" / "score.py")
assert _spec and _spec.loader
score_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score_module)


def _finding(finding_id: str, path: str, start: int, end: int) -> dict:
    return {"id": finding_id, "evidence": [{"path": path, "line_start": start, "line_end": end}]}


EXPECTED_SMALL = {
    "findings": [
        {"id": "EF-1", "title": "sql", "expected_detection": True, "evidence": [{"path": "app.py", "line_start": 10, "line_end": 12}]},
        {"id": "EF-2", "title": "control", "expected_detection": False, "evidence": [{"path": "db.py", "line_start": 5, "line_end": 5}]},
    ]
}


def test_overlapping_validated_finding_is_a_hit() -> None:
    result = score_module.score({"findings": [_finding("F-1", "app.py", 12, 20)]}, EXPECTED_SMALL)
    assert result.hits == 1 and result.passed


def test_same_lines_in_other_file_do_not_count() -> None:
    result = score_module.score({"findings": [_finding("F-1", "other.py", 10, 12)]}, EXPECTED_SMALL)
    assert result.hits == 0 and not result.passed


def test_rejected_finding_is_reported_but_does_not_count() -> None:
    dossier = {"findings": [], "rejected_findings": [_finding("F-9", "app.py", 10, 10)]}
    result = score_module.score(dossier, EXPECTED_SMALL)
    assert result.hits == 0
    assert result.results[0].outcome == "rechazado por el validador"


def test_validated_finding_on_control_is_false_positive() -> None:
    dossier = {"findings": [_finding("F-1", "app.py", 10, 10), _finding("F-2", "db.py", 5, 5)]}
    result = score_module.score(dossier, EXPECTED_SMALL)
    assert [item.id for item in result.false_positives] == ["EF-2"]
    assert not result.passed


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"findings": [_finding("F-1", "app.py", 10, 10)]}), encoding="utf-8")
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps(EXPECTED_SMALL), encoding="utf-8")
    assert score_module.main([str(good), "--expected", str(expected)]) == 0
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"findings": []}), encoding="utf-8")
    assert score_module.main([str(empty), "--expected", str(expected)]) == 1
    assert score_module.main([str(tmp_path / "missing.json")]) == 2
    assert "Recall" in capsys.readouterr().out


def test_recorded_bob_run_scores_six_of_six_against_reference() -> None:
    """Corrida real grabada (contracts/fixtures) + validador real sobre el código de la muestra."""
    result = BobAdapter.import_result(RECORDED_BOB, AUDITOR_MODE)
    dossier = build_dossier("facturaya-v1", SAMPLE, result).model_dump()
    score = score_module.score(dossier, json.loads(EXPECTED.read_text(encoding="utf-8")))
    assert (score.hits, len(score.expected)) == (6, 6)
    assert score.false_positives == []
