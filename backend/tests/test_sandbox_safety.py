"""Garantías de seguridad del sandbox (AGENTS.md: nunca ejecutar código subido por usuarios)."""

import io
import uuid
import zipfile
from pathlib import Path

import pytest

from backend.app.adapters.bob_adapter import REPO_ROOT
from backend.app.database import create_job, get_job_events, init_db
from backend.app.sandbox.test_runner import run_pytest_in_sandbox
from backend.app.worker import run_pipeline_for_job


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


def test_uploaded_zip_code_is_never_executed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un ZIP con un conftest.py malicioso atraviesa el pipeline sin que su código corra."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "pipeline.db"))
    marker = tmp_path / "pwned.txt"
    sample = REPO_ROOT / "samples" / "facturaya-v1"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        for path in sample.glob("*.*"):
            bundle.write(path, path.name)
        bundle.writestr("tests/conftest.py", f"open({str(marker)!r}, 'w').write('ejecutado')\n")
        bundle.writestr("tests/test_x.py", "def test_x():\n    assert True\n")

    init_db()
    job_id = uuid.uuid4().hex
    create_job(job_id, "zip", execution_mode="example")
    run_pipeline_for_job(job_id, "zip", zip_bytes_or_path=archive.getvalue(), requested_mode="example")

    stages = {event["stage"] for event in get_job_events(job_id)}
    assert 7 in stages, "el job debe llegar a la etapa 7 para que la prueba signifique algo"
    assert not marker.exists(), "se ejecutó código del ZIP subido por el usuario"
