"""Registro de actividad de un análisis: qué hace cada etapa mientras ocurre.

- `EventLog` escribe eventos (JSONL) en `artifacts/jobs/<id>/events.jsonl`; la API los sirve con cursor.
- `BobActivity` traduce el stream de `bob run --format stream-json` en eventos legibles: plan (todo list),
  herramientas, delegación en subagentes, razonamiento, turnos y coste.
- `inventory_events` describe el sandbox (lenguajes, líneas, carpetas) sin ejecutar nada.

Los eventos son un resumen saneado: nunca incluyen el contenido de los archivos que Bob lee, y las rutas
absolutas del servidor se convierten en rutas relativas al repositorio.
"""

import json
import re
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

EVENTS_FILE = "events.jsonl"
Stage = Literal["preparing", "auditing", "validating", "migration", "done"]

MAX_TITLE = 200
MAX_DETAIL = 600
MAX_THINKING = 480
MAX_EVENTS_PER_PAGE = 400
MAX_EVENTS = 5000  # tope por análisis: por encima solo se registran eventos esenciales
MAX_TODOS = 40
ESSENTIAL_KINDS = frozenset({"stage.start", "pipeline.failed", "bob.result", "bob.finalize", "evidence.summary",
                             "tests.summary", "tests.skipped", "dossier.ready"})
_SEQ_PREFIX = re.compile(r'^\{"seq":(\d+),')
# Rutas absolutas POSIX o Windows (no URLs): se reducen a su último componente.
_ABSOLUTE_PATH = re.compile(r"(?<![\w.:/])/(?:[^\s/\"'`<>|:]+/)+([^\s/\"'`<>|:]*)|\b[A-Za-z]:\\(?:[^\s\\\"'`<>|]+\\)*([^\s\\\"'`<>|]*)")
WRITING_STEP = 2000  # cada cuántos caracteres del JSON final se informa el progreso
_TODO = re.compile(r"^\s*\[( |x|X|-)\]\s*(.+?)\s*$")
_TASK_TAGS = re.compile(r"</?task_result>")
MAX_REPORT = 220
_WHITESPACE = re.compile(r"\s+")
# Extensiones que se cuentan como código en el inventario (el resto se agrupa como "otros").
LANGUAGES = {
    ".py": "Python", ".sql": "SQL", ".html": "HTML", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".css": "CSS", ".md": "Markdown", ".json": "JSON",
    ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML", ".ini": "INI", ".txt": "Texto",
}


class PipelineEvent(BaseModel):
    seq: int
    t: float = Field(description="Segundos desde el inicio del análisis.")
    stage: Stage
    kind: str
    actor: str
    title: str
    detail: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    recorded: bool = False


def redact_paths(text: str) -> str:
    """Nunca expone rutas del servidor: cualquier ruta absoluta queda solo con su nombre final."""
    return _ABSOLUTE_PATH.sub(lambda match: match.group(1) or match.group(2) or "…", text)


def _clip(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    text = _WHITESPACE.sub(" ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


class EventLog:
    """Registro append-only y seguro entre hilos. Un archivo JSONL por análisis."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._started = time.monotonic()
        self._offset = 0.0
        self._seq = self._last_seq()

    def _last_seq(self) -> int:
        if not self.path.is_file():
            return 0
        last = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                last = max(last, int(json.loads(line)["seq"]))
            except (ValueError, KeyError, json.JSONDecodeError):
                continue
        return last

    def now(self) -> float:
        return round(time.monotonic() - self._started + self._offset, 3)

    def advance(self, seconds: float) -> None:
        """Desplaza el reloj (al insertar una sesión grabada, lo posterior va después de ella)."""
        with self._lock:
            self._offset += max(0.0, seconds)

    def emit(self, stage: Stage, kind: str, actor: str, title: str, detail: str | None = None,
             data: dict[str, Any] | None = None, t: float | None = None, recorded: bool = False) -> PipelineEvent | None:
        with self._lock:
            if self._seq >= MAX_EVENTS and kind not in ESSENTIAL_KINDS:
                return None  # sesión anómala: el archivo no crece sin límite
            self._seq += 1
            event = PipelineEvent(
                seq=self._seq, t=self.now() if t is None else round(t, 3), stage=stage, kind=kind, actor=actor,
                title=_clip(title, MAX_TITLE) or "", detail=_clip(detail, MAX_DETAIL), data=data or {}, recorded=recorded,
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json() + "\n")
        return event


def read_events(path: Path, after: int = 0, limit: int = MAX_EVENTS_PER_PAGE) -> list[PipelineEvent]:
    """Eventos con `seq > after`, en orden. Ignora líneas corruptas (escritura interrumpida)."""
    if not path.is_file():
        return []
    events: list[PipelineEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        prefix = _SEQ_PREFIX.match(line)
        if prefix and int(prefix.group(1)) <= after:
            continue  # ya entregado: no se valida de nuevo en cada sondeo
        try:
            event = PipelineEvent.model_validate_json(line)
        except ValueError:
            continue
        if event.seq > after:
            events.append(event)
        if len(events) >= limit:
            break
    return events


# --- Inventario del sandbox ---------------------------------------------------------------

def inventory_events(workspace: Path) -> dict[str, Any]:
    """Resumen medible del repositorio copiado al sandbox (sin la configuración .bob/)."""
    languages: Counter[str] = Counter()
    python_lines = 0
    files = 0
    total_bytes = 0
    top_dirs: Counter[str] = Counter()
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace)
        if relative.parts[0] == ".bob":
            continue
        files += 1
        total_bytes += path.stat().st_size
        languages[LANGUAGES.get(path.suffix.lower(), "Otros")] += 1
        top_dirs[relative.parts[0] if len(relative.parts) > 1 else "(raíz)"] += 1
        if path.suffix.lower() == ".py":
            try:
                python_lines += sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return {
        "files": files,
        "bytes": total_bytes,
        "python_lines": python_lines,
        "languages": [{"name": name, "files": count} for name, count in languages.most_common(8)],
        "top_dirs": [{"name": name, "files": count} for name, count in top_dirs.most_common(8)],
    }


# --- Stream de Bob ------------------------------------------------------------------------

def relative_to_workspace(value: str, workspace: Path) -> str:
    """Nunca expone rutas del servidor: relativas al repo, o solo el nombre si están fuera."""
    text = value.strip()
    root = str(workspace.resolve())
    if text.startswith(root):
        text = text[len(root):].lstrip("/\\") or "."
    elif text.startswith("/") or re.match(r"^[A-Za-z]:\\", text):
        text = Path(text).name
    return text


def _strip_paths(text: str, workspace: Path) -> str:
    root = str(workspace.resolve())
    return redact_paths(text.replace(root + "/", "").replace(root, "."))


def parse_todos(raw: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for line in raw.splitlines()[:MAX_TODOS * 4]:
        if len(items) >= MAX_TODOS:
            break
        match = _TODO.match(line)
        if match:
            mark = match.group(1).lower()
            state = "done" if mark == "x" else "active" if mark == "-" else "pending"
            items.append({"state": state, "text": _clip(match.group(2), 160) or ""})
    return items


class BobActivity:
    """Convierte eventos crudos de Bob (stream-json) en eventos de la etapa `auditing`.

    El intérprete es puro respecto al contenido: no guarda salidas de herramientas ni código leído.
    """

    ORCHESTRATOR = "evidence-auditor"

    def __init__(self, log: EventLog, workspace: Path, actor: str = ORCHESTRATOR,
                 recorded: bool = False, clock: float | None = None) -> None:
        self.log = log
        self.workspace = workspace
        self.actor = actor
        self.recorded = recorded
        self.clock = clock
        self._text: list[str] = []
        self._chars = 0
        self._reported = 0
        self._turn = 0
        self._last_tokens: tuple[int, int] | None = None
        self._first_ts: float | None = None
        self._spawned: dict[str, str] = {}
        # El stream (stdout) y el log de Bob (tiempo real) llegan desde hilos distintos.
        self._lock = threading.Lock()

    def _t(self, raw: dict[str, Any]) -> float | None:
        """En una sesión grabada se conserva el ritmo original a partir de `clock`."""
        if self.clock is None:
            return None
        try:
            seconds = datetime.fromisoformat(str(raw.get("timestamp", "")).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
        if self._first_ts is None:
            self._first_ts = seconds
        return self.clock + (seconds - self._first_ts)

    def _emit(self, raw: dict[str, Any], kind: str, title: str, detail: str | None = None, data: dict[str, Any] | None = None,
              actor: str | None = None) -> None:
        self.log.emit("auditing", kind, actor or self.actor, title, detail, data, t=self._t(raw), recorded=self.recorded)

    def flush_thinking(self, raw: dict[str, Any] | None = None) -> None:
        text = "".join(self._text).strip()
        self._text = []
        self._chars = 0
        self._reported = 0
        if not text:
            return
        if text.lstrip().startswith("{") or '"findings"' in text[:200]:
            self._emit(raw or {}, "bob.answer", "Bob entregó el expediente", data={"chars": len(text)})
            return
        self._emit(raw or {}, "bob.thinking", "Razonamiento", _clip(_strip_paths(text, self.workspace), MAX_THINKING))

    def feed(self, raw: dict[str, Any]) -> None:
        with self._lock:
            self._feed(raw)

    def _feed(self, raw: dict[str, Any]) -> None:
        kind = raw.get("type")
        if kind == "message" and raw.get("role") == "assistant":
            chunk = str(raw.get("content", ""))
            self._text.append(chunk)
            self._chars += len(chunk)
            # Redactar el expediente puede tardar minutos: se informa el avance sin exponer el texto.
            if self._chars - self._reported >= WRITING_STEP and "".join(self._text).lstrip().startswith("{"):
                self._reported = self._chars - self._chars % WRITING_STEP
                self._emit(raw, "bob.writing", "Bob redacta el expediente", data={"chars": self._reported})
        elif kind == "tool_use":
            self.flush_thinking(raw)
            self._tool(raw)
        elif kind == "tool_result" and str(raw.get("tool_id")) in self._spawned:
            self._report(raw)
        elif kind == "tool_result" and raw.get("status") not in (None, "success"):
            self._emit(raw, "bob.tool.error", "Una herramienta falló", _clip(_strip_paths(str(raw.get("output", "")), self.workspace), 160))
        elif kind == "subagent_start":
            agent = str(raw.get("agentType", "subagente"))
            task = _clip(_strip_paths(str(raw.get("description", "")), self.workspace), 280)
            self._emit(raw, "bob.subagent.start", f"Delegó en {agent}", task, {"agent": agent})
        elif kind == "subagent_end":
            meta = raw.get("metadata") or {}
            agent = str(meta.get("agentType", "subagente"))
            spend = meta.get("spend") or {}
            self._emit(raw, "bob.subagent.end", f"{agent} terminó", data={
                "agent": agent,
                "tool_uses": meta.get("toolUseCount"),
                "turns": meta.get("loopTurnCount"),
                "duration_ms": meta.get("durationMs"),
                "cost": spend.get("cost"),
                "exit": meta.get("loopExitReason"),
            })
        elif kind == "cost":
            costs = raw.get("costs") or {}
            tokens = (int(costs.get("input", 0) or 0), int(costs.get("output", 0) or 0))
            if tokens != self._last_tokens:
                self._last_tokens = tokens
                self._turn += 1
                self._emit(raw, "bob.turn", f"Turno {self._turn} del orquestador",
                           data={"turn": self._turn, "input_tokens": tokens[0], "output_tokens": tokens[1]})
        elif kind == "result":
            self.flush_thinking(raw)
            stats = raw.get("stats") or {}
            self._emit(raw, "bob.result", "Sesión de Bob cerrada", data={
                "status": raw.get("status"),
                "cost": stats.get("session_costs"),
                "max_cost": stats.get("max_cost"),
                "duration_ms": stats.get("duration_ms"),
                "tool_calls": stats.get("tool_calls"),
            })

    def _report(self, raw: dict[str, Any]) -> None:
        """Informe que un subagente devuelve al orquestador: primera frase y tamaño, sin volcarlo."""
        agent = self._spawned.pop(str(raw.get("tool_id")))
        output = _TASK_TAGS.sub("", str(raw.get("output", ""))).strip()
        first = re.split(r"(?<=[.!?])\s|\n", output, maxsplit=1)[0] if output else ""
        self._emit(raw, "bob.subagent.report", f"{agent} entregó su informe al orquestador",
                   _clip(_strip_paths(first, self.workspace), MAX_REPORT),
                   {"agent": agent, "chars": len(output), "status": raw.get("status")}, actor=agent)

    def _tool(self, raw: dict[str, Any]) -> None:
        name = str(raw.get("tool_name", "herramienta"))
        params = raw.get("parameters") or {}
        path = relative_to_workspace(str(params.get("path", "")), self.workspace) if params.get("path") else None
        if name == "update_todo_list":
            items = parse_todos(_strip_paths(str(params.get("todos", "")), self.workspace))
            active = next((item["text"] for item in items if item["state"] == "active"), None)
            self._emit(raw, "bob.plan", "Bob actualizó su plan", active, {"items": items})
        elif name == "spawn_subagent":
            # El inicio en tiempo real llega del log de Bob (subagent_start); aquí solo se asocia el
            # tool_id para reconocer después el informe que el subagente devuelve al orquestador.
            self._spawned[str(raw.get("tool_id"))] = str(params.get("name", "subagente"))
        elif name == "use_skill":
            skill = str(params.get("skill_name", ""))
            self._emit(raw, "bob.skill", f"Activó la skill {skill}", data={"skill": skill})
        elif name == "read_file":
            self._emit(raw, "bob.tool", f"Leyó {path}", data={"tool": name, "target": path})
        elif name == "list_files":
            self._emit(raw, "bob.tool", f"Listó {path or '.'}", data={"tool": name, "target": path or "."})
        elif name == "glob":
            pattern = _clip(str(params.get("pattern", "")), 120)
            self._emit(raw, "bob.tool", f"Buscó archivos {pattern}", data={"tool": name, "target": pattern})
        elif name in ("search_files", "grep", "codebase_search"):
            query = _clip(str(params.get("regex") or params.get("query") or params.get("pattern") or ""), 120)
            self._emit(raw, "bob.tool", f"Buscó «{query}»" + (f" en {path}" if path else ""), data={"tool": name, "target": query})
        elif name in ("write_to_file", "apply_diff", "insert_content", "search_and_replace", "edit_file", "edit"):
            self._emit(raw, "bob.edit", f"Escribió {path}" if name == "write_to_file" else f"Editó {path}", data={"tool": name, "target": path})
        else:
            self._emit(raw, "bob.tool", f"Usó {name}", data={"tool": name, "target": path})
