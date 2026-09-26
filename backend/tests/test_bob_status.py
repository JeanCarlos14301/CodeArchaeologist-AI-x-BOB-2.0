"""Diagnóstico de Bob (/api/bob/status): la versión del CLI se calcula una vez por proceso.

`bob --version` tarda ~0.4 s en local pero ~15 s en la instancia de Render (CPU compartida), y la
página no deja iniciar un análisis hasta recibir el diagnóstico.
"""

import subprocess
from collections.abc import Callable, Iterator

import pytest

from app.jobs import service

FAKE_BINARY = "/opt/prueba/bin/bob"


@pytest.fixture(autouse=True)
def empty_cache() -> Iterator[None]:
    service._BOB_VERSIONS.pop(FAKE_BINARY, None)
    yield
    service._BOB_VERSIONS.pop(FAKE_BINARY, None)


def _fake_reader(calls: list[str], outcome: str | None | Exception) -> Callable[[str], str | None]:
    def read(binary: str) -> str | None:
        if binary != FAKE_BINARY:
            return None  # calentamientos de otras pruebas con el Bob real: no cuentan
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
    assert len(calls) == 1, "el CLI de Bob no se relanza en cada consulta"


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("bob", 45), OSError("sin permisos"), None])
def test_failed_version_check_is_not_cached(monkeypatch: pytest.MonkeyPatch, failure: Exception | None) -> None:
    calls: list[str] = []
    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, failure))
    assert service.bob_version(FAKE_BINARY) is None

    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, "2.0.5"))
    assert service.bob_version(FAKE_BINARY) == "2.0.5", "un fallo transitorio se reintenta"
    assert len(calls) == 2


def test_warm_up_makes_status_answer_from_the_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(service.shutil, "which", lambda _name: FAKE_BINARY)
    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, "2.0.5"))

    service.warm_bob_version()
    status = service.bob_status()

    assert status.installed and status.version == "2.0.5"
    assert len(calls) == 1, "la consulta usa lo calculado al arrancar"


def test_status_without_bob_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    monkeypatch.setattr(service, "_read_bob_version", _fake_reader(calls, "2.0.5"))

    service.warm_bob_version()
    status = service.bob_status()

    assert not status.installed and status.version is None
    assert calls == []
