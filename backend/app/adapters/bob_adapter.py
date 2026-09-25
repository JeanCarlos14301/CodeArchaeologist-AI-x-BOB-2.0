"""Adaptador de IBM Bob Shell (`bob run`) para el orquestador determinista (D6, D-04).

- Invoca `bob run` por subprocess con lista de argumentos, sin `shell=True`.
- El prompt viaja por stdin, así un texto que empiece por `-` nunca se interpreta como flag.
- Solo acepta modos declarados en `.bob/custom_modes.yaml` o los integrados de Bob.
- Aplica timeout, tope de coste y tope de turnos en cada invocación.
- Soporta el modo asistido (D12): importar un resultado JSON exportado de Bob.
Cada resultado lleva `execution_mode` (D8).
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

BUILTIN_MODES: frozenset[str] = frozenset({"agent", "plan", "ask"})
DEFAULT_TIMEOUT_S = 600
DEFAULT_MAX_TURNS = 30
DEFAULT_MAX_COST = 5.0
REPO_ROOT = Path(__file__).resolve().parents[3]
CUSTOM_MODES_FILE = REPO_ROOT / ".bob" / "custom_modes.yaml"
_SLUG_PATTERN = re.compile(r"^\s*-\s*slug:\s*([a-z0-9-]+)\s*$", re.MULTILINE)
_STDERR_TAIL_CHARS = 2000

ExecutionMode = Literal["live", "imported", "example"]


class BobError(RuntimeError):
    """Error base de la integración con Bob."""


class BobNotInstalledError(BobError):
    """No se encontró el ejecutable de Bob Shell."""


class BobConfigError(BobError):
    """Configuración inválida: falta API key o el modo no existe."""


class BobTimeoutError(BobError):
    """Bob no terminó dentro del tiempo permitido."""


class BobExecutionError(BobError):
    """Bob terminó con error o su salida no es un resultado válido."""


class BobStats(BaseModel):
    task_id: str
    duration_ms: int
    session_costs: float
    tool_calls: int = 0


class BobResult(BaseModel):
    mode: str
    status: str
    last_message: str
    stats: BobStats | None = None
    execution_mode: ExecutionMode


class BobRunSettings(BaseModel):
    bob_binary: str = "bob"
    timeout_s: int = Field(default=DEFAULT_TIMEOUT_S, gt=0)
    max_turns: int = Field(default=DEFAULT_MAX_TURNS, gt=0)
    max_cost: float = Field(default=DEFAULT_MAX_COST, gt=0)
    disable_mcp: bool = True
    disable_subagents: bool = False
    accept_license: bool = False

    @classmethod
    def from_env(cls) -> "BobRunSettings":
        """Lee overrides opcionales de variables de entorno."""
        overrides: dict[str, object] = {}
        env_map = {
            "BOB_BINARY": "bob_binary",
            "BOB_TIMEOUT_S": "timeout_s",
            "BOB_MAX_TURNS": "max_turns",
            "BOB_MAX_COST": "max_cost",
        }
        for env_name, field_name in env_map.items():
            value = os.environ.get(env_name)
            if value:
                overrides[field_name] = value
        if os.environ.get("BOB_ACCEPT_LICENSE", "").lower() == "true":
            overrides["accept_license"] = True
        return cls.model_validate(overrides)


def load_custom_mode_slugs(modes_file: Path = CUSTOM_MODES_FILE) -> frozenset[str]:
    """Extrae los slugs de `.bob/custom_modes.yaml` sin depender de PyYAML."""
    if not modes_file.is_file():
        return frozenset()
    return frozenset(_SLUG_PATTERN.findall(modes_file.read_text(encoding="utf-8")))


def _result_payloads(stdout: str) -> list[dict]:
    """Candidatos JSON: el documento completo (exportado con sangría) o una línea por evento."""
    candidates = [stdout.strip(), *reversed(stdout.strip().splitlines())]
    payloads: list[dict] = []
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("type") == "result":
            payloads.append(payload)
    return payloads


def parse_bob_output(stdout: str, mode: str) -> BobResult:
    """Busca el último evento `result` en la salida JSON de `bob run --format json`."""
    payloads = _result_payloads(stdout)
    if not payloads:
        raise BobExecutionError("La salida de Bob no contiene un evento 'result' JSON.")
    payload = payloads[0]
    return BobResult(
        mode=mode,
        status=payload.get("status", "unknown"),
        last_message=payload.get("last_message", ""),
        stats=BobStats.model_validate(payload["stats"]) if "stats" in payload else None,
        execution_mode="live",
    )


class BobAdapter:
    """Ejecuta modos de Bob de forma acotada y devuelve resultados tipados."""

    def __init__(
        self,
        workspace: Path,
        settings: BobRunSettings | None = None,
        allowed_modes: frozenset[str] | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.settings = settings or BobRunSettings.from_env()
        custom = load_custom_mode_slugs() if allowed_modes is None else allowed_modes
        self.allowed_modes = BUILTIN_MODES | custom

    def build_command(self, mode: str, binary_path: str) -> list[str]:
        """Construye la lista de argumentos; el prompt nunca forma parte de ella."""
        command = [
            binary_path,
            "run",
            "--format", "json",
            "--mode", mode,
            "--workspace", str(self.workspace),
            "--max-turns", str(self.settings.max_turns),
            "--max-cost", str(self.settings.max_cost),
            "--trust",
        ]
        if self.settings.disable_mcp:
            command.append("--disable-mcp")
        if self.settings.disable_subagents:
            command.append("--disable-subagents")
        if self.settings.accept_license:
            command.append("--accept-license")
        return command

    def _validate(self, mode: str, prompt: str) -> str:
        if mode not in self.allowed_modes:
            raise BobConfigError(f"Modo de Bob no permitido: {mode!r}")
        if not prompt.strip():
            raise BobConfigError("El prompt para Bob está vacío.")
        if not os.environ.get("BOB_API_KEY"):
            raise BobConfigError("Falta BOB_API_KEY en el entorno (ver .env.example).")
        if not self.workspace.is_dir():
            raise BobConfigError(f"El workspace no existe: {self.workspace}")
        binary_path = shutil.which(self.settings.bob_binary)
        if binary_path is None:
            raise BobNotInstalledError(
                f"No se encontró '{self.settings.bob_binary}'. Instala Bob Shell (ver docs/bob-usage.md)."
            )
        return binary_path

    def run(self, mode: str, prompt: str) -> BobResult:
        """Ejecuta un modo con el prompt por stdin y devuelve el resultado `live`."""
        binary_path = self._validate(mode, prompt)
        command = self.build_command(mode, binary_path)
        try:
            completed = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
                command,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.settings.timeout_s,
                cwd=self.workspace,
                env=os.environ.copy(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BobTimeoutError(
                f"Bob ({mode}) superó el timeout de {self.settings.timeout_s}s."
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout)[-_STDERR_TAIL_CHARS:].strip()
            raise BobExecutionError(
                f"Bob ({mode}) terminó con código {completed.returncode}: {detail}"
            )
        result = parse_bob_output(completed.stdout, mode)
        if result.status != "success":
            raise BobExecutionError(f"Bob ({mode}) devolvió status {result.status!r}.")
        return result

    @staticmethod
    def import_result(json_path: Path, mode: str) -> BobResult:
        """Modo asistido (D12): carga un resultado exportado de Bob como `imported`."""
        result = parse_bob_output(json_path.read_text(encoding="utf-8"), mode)
        return result.model_copy(update={"execution_mode": "imported"})
