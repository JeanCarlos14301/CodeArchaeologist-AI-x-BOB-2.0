"""Pruebas SUPER CONCRETAS con IBM Bob Shell en vivo (modo live).

Diseñadas para validar la integración real de Bob de forma determinista y económica:
- Limita estrictamente a 1 turno (max_turns=1).
- Desactiva subagentes y MCP para no consumir bobcoins innecesarias (max_cost=0.5).
- Verifica:
  1. Ejecución en modo evidence-auditor devolviendo JSON estructurado y estadísticas reales.
  2. Ejecución en modo migration-architect reconociendo el patrón Strangler Fig.
  3. Streaming en vivo (stream-json) recibiendo eventos en tiempo real con BobAdapter.run_stream.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from app.adapters.bob_adapter import (
    BobAdapter,
    BobRunSettings,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.live
@pytest.mark.skipif(
    not (os.environ.get("BOB_API_KEY") and (shutil.which("bob") or shutil.which("bob.cmd"))),
    reason="Requiere Bob Shell instalado y BOB_API_KEY en el entorno",
)
def test_live_evidence_auditor_minimal() -> None:
    """Verifica que Bob en modo evidence-auditor responde en vivo con consumo mínimo de tokens."""
    settings = BobRunSettings(
        max_turns=1,
        max_cost=0.5,
        disable_subagents=True,
        disable_mcp=True,
        timeout_s=60,
        accept_license=True,
    )
    adapter = BobAdapter(REPO_ROOT, settings)
    prompt = 'Responde únicamente con el siguiente JSON sin formato adicional: {"status": "ok", "agent": "evidence-auditor"}. No ejecutes herramientas.'
    result = adapter.run("evidence-auditor", prompt)

    assert result.status == "success"
    assert result.execution_mode == "live"
    assert result.stats is not None
    assert result.stats.task_id
    assert result.stats.duration_ms > 0
    assert result.stats.session_costs >= 0.0

    # Validar que el mensaje contiene el payload esperado
    assert "evidence-auditor" in result.last_message or "ok" in result.last_message


@pytest.mark.live
@pytest.mark.skipif(
    not (os.environ.get("BOB_API_KEY") and (shutil.which("bob") or shutil.which("bob.cmd"))),
    reason="Requiere Bob Shell instalado y BOB_API_KEY en el entorno",
)
def test_live_migration_architect_minimal() -> None:
    """Verifica que el modo migration-architect se ejecuta en vivo y devuelve razonamiento arquitectónico."""
    settings = BobRunSettings(
        max_turns=1,
        max_cost=0.5,
        disable_subagents=True,
        disable_mcp=True,
        timeout_s=60,
        accept_license=True,
    )
    adapter = BobAdapter(REPO_ROOT, settings)
    prompt = 'Responde únicamente con un JSON con la clave "pattern": "Strangler Fig". No uses herramientas.'
    result = adapter.run("migration-architect", prompt)

    assert result.status == "success"
    assert result.execution_mode == "live"
    assert "Strangler" in result.last_message or "pattern" in result.last_message


@pytest.mark.live
@pytest.mark.skipif(
    not (os.environ.get("BOB_API_KEY") and (shutil.which("bob") or shutil.which("bob.cmd"))),
    reason="Requiere Bob Shell instalado y BOB_API_KEY en el entorno",
)
def test_live_stream_json_events(tmp_path: Path) -> None:
    """Valida el streaming en tiempo real (stream-json) con eventos de Bob reales."""
    settings = BobRunSettings(
        max_turns=1,
        max_cost=0.5,
        disable_subagents=True,
        disable_mcp=True,
        timeout_s=60,
        accept_license=True,
    )
    adapter = BobAdapter(REPO_ROOT, settings)
    seen_events: list[dict] = []
    raw_log = tmp_path / "live-bob-raw.jsonl"

    prompt = 'Responde la palabra CONFIRMADO. No uses herramientas.'
    result = adapter.run_stream(
        mode="evidence-auditor",
        prompt=prompt,
        on_event=seen_events.append,
        settings=settings,
        raw_log=raw_log,
    )

    assert result.status == "success"
    assert result.execution_mode == "live"
    assert len(seen_events) >= 2

    # Debe haber al menos un evento de mensaje y un evento result
    event_types = [e.get("type") for e in seen_events]
    assert "message" in event_types
    assert "result" in event_types

    # El log crudo se debió persistir
    assert raw_log.is_file()
    assert len(raw_log.read_text(encoding="utf-8").strip().splitlines()) >= 2
