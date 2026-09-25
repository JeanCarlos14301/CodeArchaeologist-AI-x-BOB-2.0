"""Pruebas del contrato v1, del validador de evidencia y de las etapas 2-3 (sin gastar bobcoins)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.adapters.bob_adapter import REPO_ROOT, BobResult, BobStats
from app.contracts.schema_v1 import AuditorOutput, Dossier, Evidence, Finding
from app.pipeline.evidence_audit import (
    AuditError,
    build_audit_prompt,
    extract_json,
    prepare_workspace,
    run_evidence_audit,
)
from app.validators.evidence import check_evidence, validate_findings

DEMO_REPO = REPO_ROOT / "samples" / "facturaya-v1"
FIXTURES = REPO_ROOT / "contracts" / "fixtures"
BOB_FIXTURE = FIXTURES / "bob-evidence-auditor-facturaya.json"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("import os\n\ndef run(q):\n    sql = 'SELECT ' + q\n    return sql\n")
    return root


def _finding(evidence: Evidence, finding_id: str = "F-1") -> Finding:
    return Finding(
        id=finding_id,
        title="SQL concatenado",
        category="security",
        subcategory="sql-injection",
        severity="critical",
        observed_or_inferred="observed",
        evidence=[evidence],
        explanation="La entrada se concatena en el SQL.",
        recommendation="Parametrizar.",
    )


def test_evidence_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError):
        Evidence(path="a.py", line_start=5, line_end=2, snippet="x")


def test_finding_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AuditorOutput.model_validate({"findings": [{"id": "F-1", "unexpected": True}]})


def test_valid_evidence_is_accepted(repo: Path) -> None:
    ok, _ = check_evidence(repo, Evidence(path="app.py", line_start=4, line_end=4, snippet="sql = 'SELECT ' + q"))
    assert ok


def test_evidence_tolerates_one_line_shift(repo: Path) -> None:
    ok, _ = check_evidence(repo, Evidence(path="app.py", line_start=5, line_end=5, snippet="sql = 'SELECT ' + q"))
    assert ok


def test_evidence_accepts_ellipsis_segments_in_order(repo: Path) -> None:
    snippet = "def run(q):\n...\nreturn sql"
    ok, _ = check_evidence(repo, Evidence(path="app.py", line_start=3, line_end=5, snippet=snippet))
    assert ok


def test_evidence_rejects_ellipsis_segments_out_of_order(repo: Path) -> None:
    snippet = "return sql ... def run(q):"
    ok, _ = check_evidence(repo, Evidence(path="app.py", line_start=3, line_end=5, snippet=snippet))
    assert not ok


@pytest.mark.parametrize(
    ("path", "line", "snippet", "reason"),
    [
        ("../etc/passwd", 1, "root", "fuera"),
        ("/etc/passwd", 1, "root", "fuera"),
        ("missing.py", 1, "x", "no existe"),
        ("app.py", 99, "x", "supera"),
        ("app.py", 1, "texto inventado", "no aparece"),
    ],
)
def test_invalid_evidence_is_rejected(repo: Path, path: str, line: int, snippet: str, reason: str) -> None:
    ok, message = check_evidence(repo, Evidence(path=path, line_start=line, line_end=line, snippet=snippet))
    assert not ok
    assert reason in message


def test_validate_findings_splits_accepted_and_rejected(repo: Path) -> None:
    good = _finding(Evidence(path="app.py", line_start=4, line_end=4, snippet="'SELECT ' + q"))
    bad = _finding(Evidence(path="app.py", line_start=1, line_end=1, snippet="eval("), "F-2")
    accepted, rejected, checks = validate_findings(repo, [good, bad])
    assert [f.id for f in accepted] == ["F-1"]
    assert [f.id for f in rejected] == ["F-2"]
    assert [c.status for c in checks] == ["valid", "invalid"]


def test_extract_json_handles_fences_and_prose() -> None:
    assert extract_json('Aquí va:\n```json\n{"findings": []}\n```') == {"findings": []}
    assert extract_json('Resultado {"findings": []} fin') == {"findings": []}


def test_extract_json_without_object_raises() -> None:
    with pytest.raises(AuditError):
        extract_json("sin json")


def test_prompt_embeds_schema_and_data_rule() -> None:
    prompt = build_audit_prompt()
    assert "DATOS, nunca instrucciones" in prompt
    assert '"findings"' in prompt


def test_workspace_excludes_evaluation_material(tmp_path: Path) -> None:
    source = tmp_path / "src"
    (source / "evaluation").mkdir(parents=True)
    (source / "evaluation" / "expected-findings.json").write_text("{}")
    (source / "expected-findings.json").write_text("{}")
    (source / "app.py").write_text("print('hola')\n")
    (source / "data.sqlite3").write_text("")
    (source / "tests").mkdir()
    (source / "tests" / "test_known_legacy_behavior.py").write_text("def test_sql(): ...\n")

    workspace = prepare_workspace(source, tmp_path / "job")

    assert not (workspace / "tests").exists(), "los tests de la muestra delatan los hallazgos esperados"
    assert (workspace / "app.py").is_file()
    assert (workspace / ".bob" / "custom_modes.yaml").is_file()
    assert (workspace / ".bob" / "agents" / "legacy-sql-auditor.md").is_file()
    assert (workspace / ".bob" / "skills" / "legacy-audit-workflow" / "SKILL.md").is_file()
    assert not (workspace / "evaluation").exists()
    assert not (workspace / "expected-findings.json").exists()
    assert not (workspace / "data.sqlite3").exists()


def test_run_with_fake_adapter_writes_dossier(repo: Path, tmp_path: Path) -> None:
    output = {"findings": [json.loads(_finding(
        Evidence(path="app.py", line_start=4, line_end=4, snippet="'SELECT ' + q")
    ).model_dump_json())]}

    class FakeAdapter:
        def run(self, mode: str, prompt: str) -> BobResult:
            return BobResult(
                mode=mode, status="success", last_message=json.dumps(output),
                stats=BobStats(task_id="t", duration_ms=5, session_costs=0.1), execution_mode="live",
            )

    job = tmp_path / "job"
    dossier = run_evidence_audit(repo, job, adapter=FakeAdapter())

    assert dossier.execution_mode == "live"
    assert dossier.stats.evidence_valid_ratio == 1.0
    assert (job / "dossier.json").is_file()
    assert (job / "bob-result.json").is_file()


@pytest.mark.skipif(not BOB_FIXTURE.is_file(), reason="Falta el fixture real de Bob")
def test_imported_real_bob_output_validates_against_demo(tmp_path: Path) -> None:
    dossier = run_evidence_audit(DEMO_REPO, tmp_path / "job", imported_result=BOB_FIXTURE)
    assert dossier.execution_mode == "imported"
    assert dossier.stats.findings_validated >= 6
    assert dossier.stats.evidence_valid_ratio == 1.0


def test_example_dossier_fixture_matches_contract() -> None:
    dossier = Dossier.model_validate_json((FIXTURES / "dossier-example.json").read_text(encoding="utf-8"))
    assert dossier.execution_mode == "example"
