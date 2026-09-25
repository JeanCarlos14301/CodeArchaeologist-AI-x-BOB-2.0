"""Pruebas del BobAdapter: unitarias con subprocess simulado y una prueba live opcional."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from app.adapters import bob_adapter
from app.adapters.bob_adapter import (
    BobAdapter,
    BobConfigError,
    BobExecutionError,
    BobNotInstalledError,
    BobRunSettings,
    BobTimeoutError,
    load_custom_mode_slugs,
    parse_bob_output,
)

RESULT_LINE = json.dumps(
    {
        "type": "result",
        "status": "success",
        "stats": {"task_id": "abc", "duration_ms": 10, "session_costs": 0.04, "tool_calls": 0},
        "last_message": "OK",
    }
)


@pytest.fixture
def adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BobAdapter:
    monkeypatch.setenv("BOB_API_KEY", "test-key")
    monkeypatch.setattr(bob_adapter.shutil, "which", lambda _name: "/usr/local/bin/bob")
    return BobAdapter(tmp_path, BobRunSettings(), frozenset({"evidence-auditor"}))


def _fake_run(stdout: str = RESULT_LINE, returncode: int = 0, stderr: str = ""):
    calls: list[dict] = []

    def run(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    return run, calls


def test_custom_modes_file_declares_the_five_core_modes() -> None:
    slugs = load_custom_mode_slugs()
    core = {"evidence-auditor", "migration-architect", "contract-keeper", "strangler-surgeon", "board-narrator"}
    assert core <= slugs


def test_parse_bob_output_takes_last_result_event() -> None:
    stdout = "log line\n" + json.dumps({"type": "event"}) + "\n" + RESULT_LINE
    result = parse_bob_output(stdout, "ask")
    assert result.last_message == "OK"
    assert result.execution_mode == "live"
    assert result.stats is not None and result.stats.task_id == "abc"


def test_parse_bob_output_without_result_raises() -> None:
    with pytest.raises(BobExecutionError):
        parse_bob_output("Error: something", "ask")


def test_run_passes_prompt_via_stdin_not_argv(adapter: BobAdapter, monkeypatch: pytest.MonkeyPatch) -> None:
    fake, calls = _fake_run()
    monkeypatch.setattr(bob_adapter.subprocess, "run", fake)
    prompt = "--mode agent; rm -rf /"

    result = adapter.run("evidence-auditor", prompt)

    assert result.status == "success"
    call = calls[0]
    assert call["input"] == prompt
    assert prompt not in call["command"]
    assert "shell" not in call
    assert call["command"][call["command"].index("--mode") + 1] == "evidence-auditor"


def test_run_rejects_unknown_mode(adapter: BobAdapter) -> None:
    with pytest.raises(BobConfigError):
        adapter.run("modo-inexistente", "hola")


def test_run_rejects_empty_prompt(adapter: BobAdapter) -> None:
    with pytest.raises(BobConfigError):
        adapter.run("ask", "   ")


def test_run_requires_api_key(adapter: BobAdapter, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOB_API_KEY")
    with pytest.raises(BobConfigError):
        adapter.run("ask", "hola")


def test_run_reports_missing_binary(adapter: BobAdapter, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bob_adapter.shutil, "which", lambda _name: None)
    with pytest.raises(BobNotInstalledError):
        adapter.run("ask", "hola")


def test_run_maps_timeout(adapter: BobAdapter, monkeypatch: pytest.MonkeyPatch) -> None:
    def slow(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(bob_adapter.subprocess, "run", slow)
    with pytest.raises(BobTimeoutError):
        adapter.run("ask", "hola")


def test_run_maps_nonzero_exit(adapter: BobAdapter, monkeypatch: pytest.MonkeyPatch) -> None:
    fake, _ = _fake_run(stdout="", returncode=1, stderr="Error: license required")
    monkeypatch.setattr(bob_adapter.subprocess, "run", fake)
    with pytest.raises(BobExecutionError, match="license required"):
        adapter.run("ask", "hola")


def test_run_rejects_non_success_status(adapter: BobAdapter, monkeypatch: pytest.MonkeyPatch) -> None:
    fake, _ = _fake_run(stdout=RESULT_LINE.replace('"success"', '"max_cost_reached"'))
    monkeypatch.setattr(bob_adapter.subprocess, "run", fake)
    with pytest.raises(BobExecutionError):
        adapter.run("ask", "hola")


def test_build_command_applies_limits_and_flags(tmp_path: Path) -> None:
    settings = BobRunSettings(max_turns=3, max_cost=1.5, disable_subagents=True, accept_license=True)
    command = BobAdapter(tmp_path, settings, frozenset()).build_command("ask", "bob")
    assert command[command.index("--max-turns") + 1] == "3"
    assert command[command.index("--max-cost") + 1] == "1.5"
    assert {"--disable-subagents", "--accept-license", "--disable-mcp"} <= set(command)


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOB_TIMEOUT_S", "42")
    monkeypatch.setenv("BOB_ACCEPT_LICENSE", "true")
    settings = BobRunSettings.from_env()
    assert settings.timeout_s == 42
    assert settings.accept_license is True


def test_import_result_marks_imported(tmp_path: Path) -> None:
    exported = tmp_path / "bob.json"
    exported.write_text(RESULT_LINE, encoding="utf-8")
    result = BobAdapter.import_result(exported, "evidence-auditor")
    assert result.execution_mode == "imported"
    assert result.mode == "evidence-auditor"


@pytest.mark.live
@pytest.mark.skipif(
    not (os.environ.get("BOB_API_KEY") and shutil.which("bob")),
    reason="Requiere Bob Shell instalado y BOB_API_KEY",
)
def test_live_custom_mode_responds(tmp_path: Path) -> None:
    settings = BobRunSettings(max_turns=1, max_cost=0.5, disable_subagents=True, timeout_s=120)
    result = BobAdapter(bob_adapter.REPO_ROOT, settings).run(
        "evidence-auditor", "Responde solo la palabra LISTO. No uses herramientas."
    )
    assert result.execution_mode == "live"
    assert "LISTO" in result.last_message.upper()
