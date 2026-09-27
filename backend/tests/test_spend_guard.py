"""Daily bobcoin guard for a public deployment without LIVE_AUDIT_TOKEN. Spends no bobcoins."""

from pathlib import Path

import pytest

from app.adapters import bob_adapter
from app.adapters.bob_adapter import BUDGET_MESSAGE, BobAdapter, BobBudgetError, BobResult, BobStats, record_spend, spent_today
from app.jobs.assistant import AskRequest, AssistantError, ask_bob
from app.pipeline.evidence_audit import AuditError, run_evidence_audit

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "facturaya-v1"


@pytest.fixture(autouse=True)
def fresh_ledger(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bob_adapter, "_SPENT_BY_TASK", {})
    monkeypatch.delenv("BOB_DAILY_SPEND_LIMIT", raising=False)


def _result(task: str, cost: float) -> BobResult:
    return BobResult(mode="ask", status="success", last_message="{}", execution_mode="live",
                     stats=BobStats(task_id=task, duration_ms=1, session_costs=cost))


def test_resumed_sessions_are_counted_once_and_tasks_add_up() -> None:
    record_spend(_result("t1", 0.4))
    record_spend(_result("t1", 0.9))  # the same session resumed: session_costs is cumulative
    record_spend(_result("t2", 0.5))
    assert spent_today() == 1.4


def test_no_limit_means_no_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOB_API_KEY", "test-key")
    record_spend(_result("t1", 50.0))
    adapter = BobAdapter(tmp_path, settings=bob_adapter.BobRunSettings(bob_binary="definitely-not-bob"))
    with pytest.raises(bob_adapter.BobNotInstalledError):  # it got past the guard
        adapter.run("ask", "hello")


def test_reaching_the_limit_blocks_new_sessions_before_launching_bob(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOB_API_KEY", "test-key")
    monkeypatch.setenv("BOB_DAILY_SPEND_LIMIT", "1")
    record_spend(_result("t1", 1.2))
    adapter = BobAdapter(tmp_path, settings=bob_adapter.BobRunSettings(bob_binary="definitely-not-bob"))
    with pytest.raises(BobBudgetError):
        adapter.run("ask", "hello")


class _OverBudget:
    def run(self, mode: str, prompt: str) -> BobResult:
        raise BobBudgetError("Daily bobcoin limit reached (1.20 of 1).")


def test_the_limit_reaches_the_user_as_an_actionable_message(tmp_path: Path) -> None:
    with pytest.raises(AuditError, match="today's bobcoin limit"):
        run_evidence_audit(SAMPLE, tmp_path / "job", adapter=_OverBudget())
    with pytest.raises(AssistantError) as failure:
        ask_bob(SAMPLE, AskRequest(question="What is it?"), runner=_OverBudget())
    assert str(failure.value) == BUDGET_MESSAGE


def test_status_reports_the_limit_and_todays_spend(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.jobs.service import bob_status

    monkeypatch.setenv("BOB_DAILY_SPEND_LIMIT", "15")
    record_spend(_result("t1", 2.5))
    status = bob_status()
    assert status.daily_spend_limit == 15 and status.spent_today == 2.5
