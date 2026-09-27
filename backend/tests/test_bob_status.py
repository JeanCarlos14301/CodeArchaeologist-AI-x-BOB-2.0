"""Bob diagnostics (/api/bob/status): the CLI version is computed once per process.

`bob --version` takes ~0.4 s locally but ~15 s on the Render instance (shared CPU), and the
page does not let an analysis start until it receives the diagnostics.
"""

import subprocess
from collections.abc import Callable, Iterator

import pytest

from app.jobs import service

FAKE_BINARY = "/opt/test/bin/bob"


@pytest.fixture(autouse=True)
def empty_cache() -> Iterator[None]:
    service._BOB_VERSIONS.pop(FAKE_BINARY, None)
    yield
    service._BOB_VERSIONS.pop(FAKE_BINARY, None)


def _fake_reader(calls: list[str], outcome: str | None | Exception) -> Callable[[str], str | None]:
    def read(binary: str) -> str | None:
        if binary != FAKE_BINARY:
            return None  # warm-ups from other tests with the real Bob: they do not count
        calls.append(binary)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    return read


def test_version_is_computed_once_per_process(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, "2.0.5"))

    assert service.bob_version(FAKE_BINARY) == "2.0.5"
    assert service.bob_version(FAKE_BINARY) == "2.0.5"
    assert len(calls) == 1, "the Bob CLI is not relaunched on every request"


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("bob", 45), OSError("no permission"), None])
def test_failed_version_check_is_not_cached(monkeypatch: pytest.MonkeyPatch, failure: Exception | None) -> None:
    calls: list[str] = []
    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, failure))
    assert service.bob_version(FAKE_BINARY) is None

    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, "2.0.5"))
    assert service.bob_version(FAKE_BINARY) == "2.0.5", "a transient failure is retried"
    assert len(calls) == 2


def test_warm_up_makes_status_answer_from_the_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(service.shutil, "which", lambda _name: FAKE_BINARY)
    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, "2.0.5"))

    service.warm_bob_version()
    status = service.bob_status()

    assert status.installed and status.version == "2.0.5"
    assert len(calls) == 1, "the request uses what was computed at startup"


def test_status_without_bob_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, "2.0.5"))

    service.warm_bob_version()
    status = service.bob_status()

    assert not status.installed and status.version is None
    assert calls == []
