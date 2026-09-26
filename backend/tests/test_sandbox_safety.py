"""Garantías de seguridad del sandbox (AGENTS.md: nunca ejecutar código subido por usuarios)."""

import io
import uuid
import zipfile
from pathlib import Path

import pytest

from backend.app.adapters.bob_adapter import REPO_ROOT
from backend.app.pipeline.evidence_audit import run_evidence_audit
from backend.app.sandbox.test_runner import run_pytest_in_sandbox


def test_sandbox_subprocess_does_not_inherit_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOB_API_KEY", "clave-que-no-debe-filtrarse")
    monkeypatch.setenv("LIVE_AUDIT_TOKEN", "token-que-no-debe-filtrarse")
    (tmp_path / "test_env.py").write_text(
        "import os\n"
        "def test_no_credentials_visible():\n"
        "    assert 'BOB_API_KEY' not in os.environ\n"
        "    assert 'LIVE_AUDIT_TOKEN' not in os.environ\n",
        encoding="utf-8",
    )

    report = run_pytest_in_sandbox(tmp_path, timeout_seconds=60)

    assert report.passed_count == 1 and report.failed_count == 0, report.test_cases


def test_uploaded_zip_code_is_never_executed(tmp_path: Path) -> None:
    """Un ZIP con un conftest.py malicioso atraviesa el pipeline sin que su código corra."""
    marker = tmp_path / "pwned.txt"
    sample = REPO_ROOT / "samples" / "facturaya-v1"
    uploaded_repo = tmp_path / "uploaded_repo"
    uploaded_repo.mkdir()
    for path in sample.glob("*.*"):
        if path.is_file():
            (uploaded_repo / path.name).write_bytes(path.read_bytes())
    tests_dir = uploaded_repo / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "conftest.py").write_text(f"open({str(marker)!r}, 'w').write('ejecutado')\n", encoding="utf-8")
    (tests_dir / "test_x.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")

    imported = REPO_ROOT / "contracts" / "fixtures" / "bob-session-facturaya.json"
    job_dir = tmp_path / "job"

    dossier = run_evidence_audit(
        source_repo=uploaded_repo,
        job_dir=job_dir,
        imported_result=imported,
        execute_reference_cut=False,  # REGLA: nunca ejecutar pruebas de repositorios subidos
    )

    assert dossier.migration is not None
    assert dossier.migration.status == "not_run"
    assert not marker.exists(), "se ejecutó código del ZIP subido por el usuario"

