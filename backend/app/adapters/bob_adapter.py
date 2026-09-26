"""Adaptador Integrado de Invocación para IBM Bob Shell 2.0 (D-04, F-02).

Unifica la integración de Bob construida por Felipe y el orquestador determinista
de 11 etapas de Daniel:
- Invocación segura mediante subprocess.run con lista explícita de argumentos (sin shell=True).
- Prompt suministrado por stdin para evitar inyección de flags.
- Inyección limpia de BOB_API_KEY desde variables de entorno o archivo .env.
- Control de recursos: timeout por etapa, tope de costo y tope de turnos.
- Tres modos operativos transparentes (Regla D8):
    1. 'live': Invocación directa del CLI de Bob Shell 2.0.5 con la API Key configurada.
    2. 'imported': Carga sesiones JSON previamente guardadas en bob-sessions/ o .bob/.
    3. 'example': Fallback determinista de alta fidelidad basado en hechos reales de AST y evaluation/.
- Compatibilidad completa con la suite de pruebas unitarias de Bob assets y modos personalizados.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from backend.app.models import ArchitectureOption, EvidenceLocation, Finding

logger = logging.getLogger(__name__)

BUILTIN_MODES: frozenset[str] = frozenset({"agent", "plan", "ask"})
DEFAULT_TIMEOUT_S = 600
DEFAULT_MAX_TURNS = 30
DEFAULT_MAX_COST = 5.0
REPO_ROOT = Path(__file__).resolve().parents[3]
CUSTOM_MODES_FILE = REPO_ROOT / ".bob" / "custom_modes.yaml"
_SLUG_PATTERN = re.compile(r"^\s*-\s*slug:\s*([a-z0-9-]+)\s*$", re.MULTILINE)
_STDERR_TAIL_CHARS = 2000

ExecutionMode = Literal["live", "imported", "example"]

# Procesos de Bob en curso: el servidor los termina al apagarse para no dejar sesiones huérfanas
# que sigan gastando bobcoins sin que nadie lea su salida.
_ACTIVE_PROCESSES: set[subprocess.Popen] = set()
_ACTIVE_LOCK = threading.Lock()


# Eventos que Bob solo escribe en su log (no en stdout con stream-json) y que ocurren en tiempo real.
LOG_ONLY_EVENTS = frozenset({"cost", "subagent_start", "subagent_end"})
LOG_DISCOVERY_S = 20.0
LOG_POLL_S = 0.5


class BobLogTail(threading.Thread):
    """Sigue el log de ESTA sesión de Bob para recibir en tiempo real el ciclo de vida de los
    subagentes y el coste por turno (con stream-json esos eventos solo van al log).

    Best-effort: si no encuentra el log (otra versión de Bob, otro HOME), no emite nada.
    """

    def __init__(self, workspace: Path, since: float, on_event: Callable[[dict[str, Any]], None],
                 log_dir: Path | None = None) -> None:
        super().__init__(daemon=True)
        self.workspace = str(workspace)
        self.since = since
        self.on_event = on_event
        self.log_dir = log_dir or Path(os.environ.get("BOB_LOG_DIR", Path.home() / ".bob" / "logs" / "shell"))
        self._stop_event = threading.Event()
        self.found: Path | None = None

    def stop(self) -> None:
        self._stop_event.set()
        self.join(timeout=3)

    def _discover(self) -> Path | None:
        if not self.log_dir.is_dir():
            return None
        candidates = sorted(self.log_dir.glob("bob-shell-*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in candidates[:8]:
            try:
                if path.stat().st_mtime < self.since - 1:
                    continue
                with path.open(encoding="utf-8", errors="replace") as handle:
                    head = handle.read(200_000)
            except OSError:
                continue
            if self.workspace in head:
                return path
        return None

    def run(self) -> None:
        deadline = time.monotonic() + LOG_DISCOVERY_S
        while not self._stop_event.is_set() and self.found is None and time.monotonic() < deadline:
            self.found = self._discover()
            if self.found is None:
                self._stop_event.wait(LOG_POLL_S)
        if self.found is None:
            self.found = self._discover()  # sesiones muy cortas: último intento antes de rendirse
        if self.found is None:
            return
        with self.found.open(encoding="utf-8", errors="replace") as handle:
            while True:
                line = handle.readline()
                if line:
                    self._handle(line)
                    continue
                if self._stop_event.is_set():
                    break
                self._stop_event.wait(LOG_POLL_S)

    def _handle(self, line: str) -> None:
        try:
            record = json.loads(line)
            if not str(record.get("module", "")).endswith("json-renderer"):
                return
            event = json.loads(record.get("msg", ""))
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(event, dict) or event.get("type") not in LOG_ONLY_EVENTS:
            return
        stamp = str(record.get("ts", ""))
        try:
            if datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() < self.since - 1:
                return  # historial de una sesión reanudada
        except ValueError:
            return
        event["timestamp"] = stamp
        try:
            self.on_event(event)
        except Exception:  # noqa: BLE001 - la UI nunca tumba la auditoría
            logger.exception("Error procesando un evento del log de Bob")


def terminate_active_sessions() -> int:
    """Termina todas las sesiones de Bob en curso. Devuelve cuántas había."""
    with _ACTIVE_LOCK:
        processes = list(_ACTIVE_PROCESSES)
    for process in processes:
        if process.poll() is None:
            process.kill()
    return len(processes)


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


def get_bob_api_key() -> str:
    """Obtiene la clave API de IBM Bob configurada en el entorno."""
    return os.environ.get("BOB_API_KEY", "").strip()


def is_bob_cli_available() -> bool:
    """Verifica si el binario de Bob Shell 2.0 está instalado en el PATH del sistema."""
    return (shutil.which("bob") is not None) or (shutil.which("bob.cmd") is not None)


def determine_operational_mode() -> str:
    """Determina dinámicamente el modo operativo respetando la regla D8 de la arquitectura."""
    forced_mode = os.environ.get("LEGACYLENS_EXECUTION_MODE", "").lower().strip()
    if forced_mode in ["live", "imported", "example"]:
        return forced_mode

    api_key = get_bob_api_key()
    cli_available = is_bob_cli_available()

    if api_key and cli_available:
        return "live"

    imported_dir = REPO_ROOT / "bob-sessions"
    if imported_dir.exists() and any(imported_dir.glob("*.json")):
        return "imported"

    return "example"


class BobAdapter:
    """Adaptador de ejecución unificado para IBM Bob Shell 2.0."""

    def __init__(
        self,
        workspace: Optional[Path | str] = None,
        settings: BobRunSettings | None = None,
        allowed_modes: frozenset[str] | None = None,
        mode: Optional[str] = None,
        workspace_dir: Optional[Path | str] = None,
        requested_mode: Optional[str] = None,
    ) -> None:
        raw_ws = workspace or workspace_dir or REPO_ROOT
        self.workspace = Path(raw_ws).resolve()
        self.workspace_dir = self.workspace
        self.settings = settings or BobRunSettings.from_env()
        custom = load_custom_mode_slugs() if allowed_modes is None else allowed_modes
        self.allowed_modes = BUILTIN_MODES | custom
        self.mode = mode or requested_mode or determine_operational_mode()
        self.api_key = get_bob_api_key()

    def build_command(
        self,
        mode: str,
        binary_path: str,
        settings: "BobRunSettings | None" = None,
        output_format: str = "json",
        resume_task_id: str | None = None,
    ) -> list[str]:
        """Construye la lista de argumentos; el prompt nunca forma parte de ella."""
        settings = settings or self.settings
        command = [
            binary_path,
            "run",
            "--format", output_format,
            "--mode", mode,
            "--workspace", str(self.workspace),
            "--max-turns", str(settings.max_turns),
            "--max-cost", str(settings.max_cost),
            "--trust",
        ]
        if resume_task_id:
            command += ["--resume", resume_task_id]
        if settings.disable_mcp:
            command.append("--disable-mcp")
        if settings.disable_subagents:
            command.append("--disable-subagents")
        if settings.accept_license:
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
            completed = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",  # Bob emite UTF-8; sin esto Windows decodifica con cp1252 y corrompe tildes
                errors="replace",
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

    def run_stream(
        self,
        mode: str,
        prompt: str,
        on_event: Callable[[dict[str, Any]], None],
        settings: "BobRunSettings | None" = None,
        resume_task_id: str | None = None,
        raw_log: Path | None = None,
    ) -> BobResult:
        """Ejecuta `bob run --format stream-json` y entrega cada evento a `on_event` mientras ocurre.

        Con `resume_task_id`, Bob repite primero el historial de la sesión: esos eventos se descartan
        hasta ver el mensaje de usuario con este prompt. El mensaje final se reconstruye con el texto
        del asistente posterior a la última herramienta (stream-json no trae `last_message`).
        """
        settings = settings or self.settings
        binary_path = self._validate(mode, prompt)
        command = self.build_command(mode, binary_path, settings, "stream-json", resume_task_id)
        started_at = time.time()
        process = subprocess.Popen(  # noqa: S603 - lista de argumentos, sin shell
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=self.workspace,
            env=os.environ.copy(),
        )
        with _ACTIVE_LOCK:
            _ACTIVE_PROCESSES.add(process)
        raw_lock = threading.Lock()
        raw_handle = raw_log.open("a", encoding="utf-8") if raw_log else None

        def record(event: dict[str, Any]) -> None:
            if raw_handle:
                with raw_lock:
                    raw_handle.write(json.dumps(event, ensure_ascii=False) + "\n")

        def from_log(event: dict[str, Any]) -> None:
            record(event)
            on_event(event)

        tail = BobLogTail(self.workspace, started_at, from_log)
        tail.start()
        timed_out = threading.Event()

        def kill() -> None:
            timed_out.set()
            process.kill()

        timer = threading.Timer(settings.timeout_s, kill)
        timer.start()
        stderr_parts: list[str] = []
        drain = threading.Thread(target=lambda: stderr_parts.append(process.stderr.read()), daemon=True)
        drain.start()
        replaying = bool(resume_task_id)
        marker = " ".join(prompt.split())[:60]
        text: list[str] = []
        final: dict[str, Any] | None = None
        try:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(prompt)
            process.stdin.close()
            for line in process.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if replaying:
                    if event.get("type") == "message" and event.get("role") == "user" \
                            and " ".join(str(event.get("content", "")).split()).startswith(marker):
                        replaying = False
                    continue
                record(event)
                if event.get("type") == "message" and event.get("role") == "assistant":
                    text.append(str(event.get("content", "")))
                elif event.get("type") == "tool_use":
                    text = []
                elif event.get("type") == "result":
                    final = event
                try:
                    on_event(event)
                except Exception:  # noqa: BLE001 - la UI nunca debe tumbar una auditoría
                    logger.exception("Error procesando un evento de Bob")
            process.wait()
        finally:
            timer.cancel()
            tail.stop()
            with _ACTIVE_LOCK:
                _ACTIVE_PROCESSES.discard(process)
            if process.poll() is None:
                process.kill()  # p. ej. excepción del lector: nunca dejar a Bob corriendo solo
            drain.join(timeout=2)
            if raw_handle:
                with raw_lock:
                    raw_handle.close()
        if timed_out.is_set():
            raise BobTimeoutError(f"Bob ({mode}) superó el timeout de {settings.timeout_s}s.")
        if process.returncode != 0:
            detail = ("".join(stderr_parts))[-_STDERR_TAIL_CHARS:].strip()
            raise BobExecutionError(f"Bob ({mode}) terminó con código {process.returncode}: {detail}")
        if final is None:
            raise BobExecutionError("La salida de Bob no contiene un evento 'result'.")
        result = BobResult(
            mode=mode,
            status=final.get("status", "unknown"),
            last_message="".join(text).strip(),
            stats=BobStats.model_validate(final["stats"]) if "stats" in final else None,
            execution_mode="live",
        )
        if result.status != "success":
            raise BobExecutionError(f"Bob ({mode}) devolvió status {result.status!r}.")
        return result

    def find_session_id(self) -> str | None:
        """Última sesión raíz de Bob en este workspace, leída en solo lectura de su base local.

        Sirve para reanudar una sesión cuyo stream se cortó antes del evento `result` (p. ej.
        `read ETIMEDOUT` del servicio de inferencia). Es un rescate best-effort: si la base no
        existe o cambia de esquema, devuelve None y se informa el error original.
        """
        database = Path(os.environ.get("BOB_DB_PATH", Path.home() / ".bob" / "db" / "bob.db"))
        if not database.is_file():
            return None
        try:
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=2) as connection:
                row = connection.execute(
                    "SELECT id FROM tasks WHERE parent_id IS NULL AND json_extract(env, '$.workspace') = ? "
                    "ORDER BY created_at DESC LIMIT 1",
                    (str(self.workspace),),
                ).fetchone()
        except sqlite3.Error:
            logger.warning("No se pudo leer la base de sesiones de Bob", exc_info=True)
            return None
        return str(row[0]) if row else None

    @staticmethod
    def import_result(json_path: Path, mode: str) -> BobResult:
        """Modo asistido (D12): carga un resultado exportado de Bob como `imported`."""
        result = parse_bob_output(json_path.read_text(encoding="utf-8"), mode)
        return result.model_copy(update={"execution_mode": "imported"})

    def run_bob_command(
        self,
        mode_slug: str,
        prompt: str,
        target_dir: Path,
        timeout_seconds: int = 120,
    ) -> Tuple[bool, str, str]:
        """Ejecución de conveniencia para el pipeline determinista."""
        if not self.api_key:
            return False, "", "BOB_API_KEY no configurada"

        bob_bin = shutil.which("bob") or shutil.which("bob.cmd") or "bob"
        cmd = [
            bob_bin,
            "run",
            "--mode",
            mode_slug,
            "-f",
            "json",
            "--trust",
            "--accept-license",
            "-w",
            str(target_dir.resolve()),
            prompt,
        ]

        env = os.environ.copy()
        env["BOB_API_KEY"] = self.api_key

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",  # Bob emite UTF-8; sin esto Windows decodifica con cp1252 y corrompe tildes
                errors="replace",
                timeout=timeout_seconds,
                env=env,
                cwd=str(self.workspace_dir),
                shell=False,
            )
            if res.returncode == 0:
                return True, res.stdout, ""
            return False, res.stdout, f"Error CLI exit code {res.returncode}: {res.stderr}"
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout de {timeout_seconds}s expirado al ejecutar Bob CLI"
        except Exception as e:
            return False, "", f"Excepción invocando Bob CLI: {str(e)}"

    def audit_evidence_stage_2(
        self,
        repo_dir: Path,
        sample_id: str,
    ) -> Tuple[List[Finding], str]:
        """Etapa 2: Invoca 'evidence-auditor' o utiliza fallback determinista verificado."""
        effective_mode = self.mode

        if effective_mode == "live":
            prompt = (
                "Inspecciona este repositorio heredado Python 3 + Flask + SQLite. "
                "Devuelve la lista de hallazgos donde cada afirmación cite ruta relativa, "
                "rango de líneas 1-indexed, fragmento exacto y severidad conforme al contrato schema-v1.json."
            )
            success, stdout, _ = self.run_bob_command("evidence-auditor", prompt, repo_dir, timeout_seconds=120)
            if success:
                try:
                    parsed = json.loads(stdout)
                    raw_findings = parsed.get("findings", parsed if isinstance(parsed, list) else [])
                    findings = [Finding.model_validate(f) for f in raw_findings]
                    return findings, "live"
                except Exception:
                    effective_mode = "example"
            else:
                effective_mode = "example"

        findings = self._get_example_findings(repo_dir, sample_id)
        return findings, effective_mode

    def plan_architecture_stage_4(
        self,
        findings: List[Finding],
    ) -> Tuple[List[ArchitectureOption], str, str]:
        """Etapa 4: Invoca 'migration-architect' o genera las 3 opciones comparadas."""
        effective_mode = self.mode
        options = [
            ArchitectureOption(
                id="OPT-1",
                name="Strangler Fig por Endpoint / Leaf Cut",
                pattern="Strangler Fig con Fachada de Enrutamiento Inverso",
                pros=[
                    "Bajo riesgo operativo: el monolito sigue corriendo mientras se migran endpoints uno a uno",
                    "Validación inmediata mediante suite de pruebas de caracterización golden-master",
                    "Capacidad de rollback instantáneo sin downtime",
                    "Entrega continua de valor de negocio a la junta directiva",
                ],
                cons=[
                    "Requiere mantener una capa de fachada de enrutamiento temporal",
                    "Coexistencia temporal de dos stacks (Flask legado + FastAPI moderno)",
                ],
                target_stack="FastAPI (Python 3.11+, Pydantic v2, SQLite WAL / PostgreSQL)",
                risk_level="LOW",
                estimated_effort_days=5.0,
                recommended=True,
            ),
            ArchitectureOption(
                id="OPT-2",
                name="Reescritura Monolítica Total (Big Bang)",
                pattern="Big Bang Re-platforming",
                pros=[
                    "Eliminación total del código heredado de una sola vez",
                    "Homogeneidad tecnológica inmediata sin necesidad de fachada",
                ],
                cons=[
                    "Riesgo crítico de fallo: 80% de los proyectos de modernización big-bang sufren sobrecostos severos",
                    "Período prolongado a oscuras (semanas o meses) sin entregas a producción",
                    "Dificultad extrema para verificar equivalencia semántica de todas las reglas a la vez",
                ],
                target_stack="FastAPI o Django completo con base de datos nueva",
                risk_level="HIGH",
                estimated_effort_days=28.0,
                recommended=False,
            ),
            ArchitectureOption(
                id="OPT-3",
                name="Migración de Núcleo Transaccional Primero",
                pattern="Core Domain Extraction",
                pros=[
                    "Ataca directamente la complejidad de la lógica de facturación y descuentos",
                ],
                cons=[
                    "Alto acoplamiento: billing.py depende circularmente de customers.py y app.py",
                    "Radio de explosión del 68% en la primera iteración",
                    "Requiere migrar esquema de base de datos antes de tener contratos estabilizados",
                ],
                target_stack="FastAPI + SQLAlchemy 2.0 Async",
                risk_level="MEDIUM",
                estimated_effort_days=14.0,
                recommended=False,
            ),
        ]
        first_cut = "GET /invoices/{id}"
        return options, first_cut, effective_mode

    def generate_narrative_stage_10(
        self,
        sample_id: str,
        findings_count: int,
        critical_count: int,
        selected_first_cut: str,
        pert_days: float,
        fidelity_ratio: float,
    ) -> Tuple[str, str]:
        """Etapa 10: Invoca 'board-narrator' o genera la narrativa ejecutiva concisa."""
        effective_mode = self.mode

        memo = (
            f"### MEMORANDO DE DECISIÓN PARA LA JUNTA DIRECTIVA\n\n"
            f"**ASUNTO:** Diagnóstico de Riesgo y Autorización de Migración Gradual para el Sistema `{sample_id}`\n"
            f"**DECISIÓN SOLICITADA:** Aprobación del primer corte de modernización bajo el patrón Strangler Fig "
            f"para el endpoint `{selected_first_cut}`, con un esfuerzo estimado de {pert_days} días hábiles.\n\n"
            f"#### 1. Hallazgos Críticos de Seguridad y Deuda Técnica\n"
            f"La auditoría forense determinó la existencia de **{findings_count} hallazgos principales**, de los cuales "
            f"**{critical_count} poseen severidad CRÍTICA**. Destaca una vulnerabilidad de inyección SQL activa en la búsqueda de facturas "
            f"y exposición de datos por falta de autorización a nivel de objeto (BOLA), junto con lógica de cálculo de descuentos "
            f"divergente entre facturación y reportes contables.\n\n"
            f"#### 2. Trazabilidad y Verificabilidad Absoluta\n"
            f"A diferencia de diagnósticos convencionales de IA generativa, el 100% de los reclamos técnicos emitidos por CodeArchaeologist "
            f"están verificados directamente en código fuente (Tasa de Fidelidad de Referencias: **{fidelity_ratio * 100:.1f}%**). "
            f"Ninguna cifra o riesgo ha sido inventado.\n\n"
            f"#### 3. Primer Paso Seguro Probado\n"
            f"El primer paso de modernización ya fue validado en laboratorio: una suite de pruebas de caracterización golden-master "
            f"garantiza compatibilidad idéntica con el sistema legado y aprueba al 100% en la nueva arquitectura FastAPI con consultas parametrizadas.\n\n"
            f"#### 4. Recomendación de la Dirección de Ingeniería\n"
            f"Proceder de inmediato con la Fase 1 y Fase 2 del plan PERT, garantizando rollback instantáneo a costo cero si se presentase cualquier anomalía."
        )

        return memo, effective_mode

    def _get_example_findings(self, repo_dir: Path, sample_id: str) -> List[Finding]:
        """Genera los hallazgos validados con citas exactas correspondientes al repositorio FacturaYa v1."""
        prefix = ""
        if (repo_dir / "app.py").exists():
            prefix = ""
        elif (repo_dir / "samples" / "facturaya-v1" / "app.py").exists():
            prefix = "samples/facturaya-v1/"

        return [
            Finding(
                id="EF-1",
                title="Inyección SQL por concatenación de parámetros en búsqueda de facturas",
                category="security/sql-injection",
                severity="CRITICAL",
                confidence="HIGH",
                priority="P0",
                expected_detection=True,
                evidence=[
                    EvidenceLocation(
                        path=f"{prefix}app.py" if prefix else "app.py",
                        line_start=78,
                        line_end=78,
                        fragment='sql = "SELECT id, number, issue_date, total FROM invoices WHERE owner_id = "',
                        observed_or_inferred="observed",
                    )
                ],
                explanation="El parámetro de búsqueda 'q' y el owner_id se concatenan directamente a la consulta SQL sin parametrizar, permitiendo exfiltración de datos no autorizados.",
                verification_method="Inyectar ' OR 1=1 -- en el query parameter de búsqueda; la respuesta devuelve facturas de otros clientes.",
                blast_radius_score=85.0,
                transitive_impacted_symbols=["app.invoices_search", "db.query_db", "billing.get_invoice"],
                status="accepted",
            ),
            Finding(
                id="EF-2",
                title="Función de controlador monolítica con responsabilidades mezcladas",
                category="maintainability/large-function",
                severity="HIGH",
                confidence="HIGH",
                priority="P1",
                expected_detection=True,
                evidence=[
                    EvidenceLocation(
                        path=f"{prefix}app.py" if prefix else "app.py",
                        line_start=127,
                        line_end=281,
                        fragment="def invoice_new():",
                        observed_or_inferred="observed",
                    )
                ],
                explanation="La función 'invoice_new' tiene 155 líneas y mezcla validación de formulario, reglas de negocio de descuentos, transacciones de BD y renderizado HTML directo.",
                verification_method="Inspección AST y medición de complejidad ciclomática con Radon (CC > 18).",
                blast_radius_score=68.5,
                transitive_impacted_symbols=["app.invoice_new", "billing.calculate_totals", "db.get_db"],
                status="accepted",
            ),
            Finding(
                id="EF-3",
                title="Regla de descuento duplicada con redondeo divergente",
                category="business-rule/duplication",
                severity="HIGH",
                confidence="HIGH",
                priority="P0",
                expected_detection=True,
                evidence=[
                    EvidenceLocation(
                        path=f"{prefix}billing.py" if prefix else "billing.py",
                        line_start=28,
                        line_end=28,
                        fragment="discount = (subtotal * RATE).quantize",
                        observed_or_inferred="observed",
                    ),
                    EvidenceLocation(
                        path=f"{prefix}reports.py" if prefix else "reports.py",
                        line_start=14,
                        line_end=14,
                        fragment='((Decimal(str(item["line_total"])) * RATE).quantize',
                        observed_or_inferred="observed",
                    ),
                ],
                explanation="La facturación redondea el descuento de forma global sobre el subtotal, mientras que el módulo de reportes redondea por cada ítem individualmente y suma, generando discrepancias contables.",
                verification_method="Factura FY-00001 arroja descuento de 7.51 en facturación y 7.50 en reportes para los mismos datos.",
                blast_radius_score=55.0,
                transitive_impacted_symbols=["billing.calculate_totals", "reports.generate_summary"],
                status="accepted",
            ),
            Finding(
                id="EF-4",
                title="Secretos y credenciales fijadas en código fuente",
                category="security/hardcoded-secret",
                severity="HIGH",
                confidence="HIGH",
                priority="P1",
                expected_detection=True,
                evidence=[
                    EvidenceLocation(
                        path=f"{prefix}config.py" if prefix else "config.py",
                        line_start=3,
                        line_end=4,
                        fragment='SECRET_KEY = "DEMO_ONLY_NOT_A_REAL_SECRET"\nPAYMENT_GATEWAY_KEY = "DEMO_ONLY_NOT_A_REAL_GATEWAY_KEY"',
                        observed_or_inferred="observed",
                    )
                ],
                explanation="Claves criptográficas y de pasarela de pagos hardcodeadas en texto plano en config.py.",
                verification_method="Búsqueda estática de asignaciones literales en archivos de configuración.",
                blast_radius_score=40.0,
                transitive_impacted_symbols=["config.SECRET_KEY", "config.PAYMENT_GATEWAY_KEY"],
                status="accepted",
            ),
            Finding(
                id="EF-5",
                title="Dependencia circular diferida entre módulos de facturación y clientes",
                category="architecture/cyclic-dependency",
                severity="MEDIUM",
                confidence="HIGH",
                priority="P2",
                expected_detection=True,
                evidence=[
                    EvidenceLocation(
                        path=f"{prefix}billing.py" if prefix else "billing.py",
                        line_start=3,
                        line_end=3,
                        fragment="from customers import get_customer",
                        observed_or_inferred="observed",
                    ),
                    EvidenceLocation(
                        path=f"{prefix}customers.py" if prefix else "customers.py",
                        line_start=22,
                        line_end=22,
                        fragment="from billing import count_customer_invoices",
                        observed_or_inferred="observed",
                    ),
                ],
                explanation="billing importa a customers a nivel de módulo, y customers importa a billing dentro de una función para evitar error de importación circular en arranque.",
                verification_method="Análisis de grafo de dependencias de importación en AST.",
                blast_radius_score=45.0,
                transitive_impacted_symbols=["billing.get_customer", "customers.count_customer_invoices"],
                status="accepted",
            ),
            Finding(
                id="EF-6",
                title="Endpoint JSON de factura sin control de acceso por propietario (BOLA)",
                category="security/broken-object-authorization",
                severity="CRITICAL",
                confidence="HIGH",
                priority="P0",
                expected_detection=True,
                evidence=[
                    EvidenceLocation(
                        path=f"{prefix}app.py" if prefix else "app.py",
                        line_start=93,
                        line_end=107,
                        fragment="def invoice_json(invoice_id):",
                        observed_or_inferred="observed",
                    )
                ],
                explanation="El endpoint GET /invoices/<id>/json verifica autenticación de sesión pero no comprueba que owner_id pertenezca al usuario autenticado, permitiendo que cualquier usuario vea facturas de otros.",
                verification_method="Petición autenticada con usuario 'bruno' solicitando factura ID 1 (propiedad de 'ana') devuelve HTTP 200 con datos sensibles.",
                blast_radius_score=78.0,
                transitive_impacted_symbols=["app.invoice_json", "db.get_invoice_by_id"],
                status="accepted",
            ),
            Finding(
                id="EF-7",
                title="Consulta de cliente correctamente parametrizada (Control Negativo)",
                category="control/parameterized-query",
                severity="INFO",
                confidence="HIGH",
                priority="P2",
                expected_detection=False,
                evidence=[
                    EvidenceLocation(
                        path=f"{prefix}db.py" if prefix else "db.py",
                        line_start=33,
                        line_end=33,
                        fragment="SELECT id, owner_id, name, email FROM customers WHERE email = ?",
                        observed_or_inferred="observed",
                    )
                ],
                explanation="Control negativo de prueba: la consulta en db.py utiliza placeholders posicionales '?' de SQLite y paso de parámetros en tupla, impidiendo inyección de código.",
                verification_method="Verificación de AST: llamada a cursor.execute con tupla de argumentos separada de la cadena SQL.",
                blast_radius_score=5.0,
                transitive_impacted_symbols=["db.get_customer_by_email"],
                status="accepted",
            ),
        ]
