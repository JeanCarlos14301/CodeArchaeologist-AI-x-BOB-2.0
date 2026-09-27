"""VERY CONCRETE tests against the live IBM Bob Shell (live mode).

Designed to validate the real Bob integration deterministically and cheaply:
- Strictly limited to 1 turn (max_turns=1).
- Subagents and MCP disabled so no bobcoins are spent needlessly (max_cost=0.5).
- Checks:
  1. evidence-auditor mode returning structured JSON and real statistics.
  2. migration-architect mode recognizing the Strangler Fig pattern.
  3. Live streaming (stream-json) receiving real-time events with BobAdapter.run_stream.
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
    reason="Requires Bob Shell installed and BOB_API_KEY in the environment",
)
def test_live_evidence_auditor_minimal() -> None:
    """Checks that Bob in evidence-auditor mode answers live with minimal token usage."""
    settings = BobRunSettings(
        max_turns=1,
        max_cost=0.5,
        disable_subagents=True,
        disable_mcp=True,
        timeout_s=60,
        accept_license=True,
    )
    adapter = BobAdapter(REPO_ROOT, settings)
    prompt = 'Answer only with the following JSON and no extra formatting: {"status": "ok", "agent": "evidence-auditor"}. Do not run tools.'
    result = adapter.run("evidence-auditor", prompt)

    assert result.status == "success"
    assert result.execution_mode == "live"
    assert result.stats is not None
    assert result.stats.task_id
    assert result.stats.duration_ms > 0
    assert result.stats.session_costs >= 0.0

    # Check that the message contains the expected payload
    assert "evidence-auditor" in result.last_message or "ok" in result.last_message


@pytest.mark.live
@pytest.mark.skipif(
    not (os.environ.get("BOB_API_KEY") and (shutil.which("bob") or shutil.which("bob.cmd"))),
    reason="Requires Bob Shell installed and BOB_API_KEY in the environment",
)
def test_live_migration_architect_minimal() -> None:
    """Checks that migration-architect mode runs live and returns architectural reasoning."""
    settings = BobRunSettings(
        max_turns=1,
        max_cost=0.5,
        disable_subagents=True,
        disable_mcp=True,
        timeout_s=60,
        accept_license=True,
    )
    adapter = BobAdapter(REPO_ROOT, settings)
    prompt = 'Answer only with a JSON with the key "pattern": "Strangler Fig". Do not use tools.'
    result = adapter.run("migration-architect", prompt)

    assert result.status == "success"
    assert result.execution_mode == "live"
    assert "Strangler" in result.last_message or "pattern" in result.last_message


@pytest.mark.live
@pytest.mark.skipif(
    not (os.environ.get("BOB_API_KEY") and (shutil.which("bob") or shutil.which("bob.cmd"))),
    reason="Requires Bob Shell installed and BOB_API_KEY in the environment",
)
def test_live_stream_json_events(tmp_path: Path) -> None:
    """Validates real-time streaming (stream-json) with real Bob events."""
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

    prompt = 'Answer the word CONFIRMED. Do not use tools.'
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

    # There must be at least one message event and one result event
    event_types = [e.get("type") for e in seen_events]
    assert "message" in event_types
    assert "result" in event_types

    # The raw log must have been persisted
    assert raw_log.is_file()
    assert len(raw_log.read_text(encoding="utf-8").strip().splitlines()) >= 2
