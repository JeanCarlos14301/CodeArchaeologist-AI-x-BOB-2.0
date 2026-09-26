"""Orquestación del Estudio de modernización: estado en disco por análisis, transiciones y una sola sesión de Bob a la vez.

Fases: idle -> assessing -> assessed -> planning -> planned -> implementing -> implemented (o failed).
Nada se ejecuta sin que la persona lo pida; implementar exige una confirmación explícita.
"""

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.bob_adapter import BobAdapter, BobRunSettings
from app.modernization import planner
from app.modernization.catalog import targets_for
from app.modernization.implement import DIFF_NAME, ZIP_NAME, prepare_work, run_implementation
from app.modernization.models import (
    AssessRequest,
    Mapping,
    Phase,
    StudioEvent,
    StudioState,
)
from app.modernization.planner import PlannerError, Runner
from app.modernization.stack_scan import StackReport, scan_stack
from app.contracts.schema_v1 import Dossier
from app.pipeline.activity import BobActivity, redact_paths

logger = logging.getLogger(__name__)

STATE_FILE = "state.json"
STACK_FILE = "stack.json"
MAX_EVENTS = 200

_IO_LOCK = threading.RLock()
_BOB_LOCK = threading.Lock()  # una sola sesión de Bob de modernización a la vez en todo el servidor

AdapterFactory = Callable[[Path, str], Runner]


class _StudioLog:
    """Recibe los eventos de BobActivity (misma interfaz que EventLog) y los guarda como actividad del Estudio."""

    def __init__(self, studio: "Studio", phase: str, step_id: str | None = None) -> None:
        self.studio, self.phase, self.step_id = studio, phase, step_id

    def emit(self, stage: str, kind: str, actor: str, title: str, detail: str | None = None,
             data: dict | None = None, t: float | None = None, recorded: bool = False) -> None:
        flat = {k: v for k, v in (data or {}).items() if isinstance(v, (str, int, float)) or v is None}
        self.studio._event(self.phase, title, self.step_id, kind=kind, actor=actor, detail=detail, data=flat)


class StudioBusyError(RuntimeError):
    """Ya hay una operación de modernización con Bob en curso."""


class StudioStateError(RuntimeError):
    """La operación no es válida en la fase actual."""


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def default_adapter(work: Path, kind: str) -> Runner:
    """`planner` (solo lectura) o `surgeon` (edita la copia). Topes propios, ajustables por entorno."""
    base = BobRunSettings.from_env()
    if kind == "surgeon":
        settings = base.model_copy(update={
            "max_turns": max(base.max_turns, 60),
            "max_cost": _env_float("MODERNIZE_STEP_MAX_COST", 3.0),
            "timeout_s": max(base.timeout_s, 900),
        })
    else:
        settings = base.model_copy(update={
            "max_turns": max(base.max_turns, 30),
            "max_cost": _env_float("MODERNIZE_PLAN_MAX_COST", 1.5),
            "timeout_s": max(base.timeout_s, 420),
        })
    return BobAdapter(work, settings=settings)


class Studio:
    def __init__(self, job_dir: Path, project_name: str = "proyecto", adapter_factory: AdapterFactory = default_adapter) -> None:
        self.job_dir = job_dir
        self.dir = job_dir / "modernization"
        self.project_name = project_name
        self.adapter_factory = adapter_factory

    # ------------------------------------------------------------ archivos
    @property
    def source(self) -> Path:
        """Código original: la copia íntegra guardada al subir o, en análisis antiguos, el workspace de la auditoría."""
        for name in ("source", "workspace"):
            candidate = self.job_dir / name
            if candidate.is_dir():
                return candidate
        raise StudioStateError("El código de este análisis ya no está disponible en el servidor.")

    @property
    def work(self) -> Path:
        return self.dir / "work"

    def artifact(self, name: str) -> Path | None:
        path = self.dir / name
        return path if name in {ZIP_NAME, DIFF_NAME} and path.is_file() else None

    # ------------------------------------------------------------ estado
    def state(self) -> StudioState:
        with _IO_LOCK:
            path = self.dir / STATE_FILE
            if not path.is_file():
                return StudioState()
            try:
                return StudioState.model_validate_json(path.read_text(encoding="utf-8"))
            except ValueError:
                logger.warning("Estado de modernización ilegible en %s", self.dir.name)
                return StudioState()

    def _save(self, state: StudioState) -> None:
        with _IO_LOCK:
            self.dir.mkdir(parents=True, exist_ok=True)
            state.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            state.events = state.events[-MAX_EVENTS:]
            temp = self.dir / (STATE_FILE + ".tmp")
            temp.write_text(state.model_dump_json(indent=1), encoding="utf-8")
            temp.replace(self.dir / STATE_FILE)

    def _update(self, **changes: object) -> StudioState:
        with _IO_LOCK:
            state = self.state()
            for key, value in changes.items():
                setattr(state, key, value)
            self._save(state)
            return state

    def _event(self, phase: str, message: str, step_id: str | None = None, kind: str = "info", actor: str | None = None,
               detail: str | None = None, data: dict | None = None) -> None:
        with _IO_LOCK:
            state = self.state()
            state.events.append(StudioEvent(
                t=round(time.time(), 1), phase=phase, message=redact_paths(message)[:300], step_id=step_id, kind=kind, actor=actor,
                detail=redact_paths(detail)[:400] if detail else None, data=data or {},
            ))
            self._save(state)

    def _sink(self, phase: str, actor: str, step_id: str | None = None):
        """Convierte el stream de Bob en actividad real (lecturas, búsquedas, subagentes, ediciones)."""
        return BobActivity(_StudioLog(self, phase, step_id), self.work, actor=actor).feed

    def findings_digest(self) -> str:
        """Hallazgos ya validados de la auditoría (si la hubo): títulos y ubicaciones, sin código."""
        path = self.job_dir / "dossier.json"
        if not path.is_file():
            return "[]"
        try:
            dossier = Dossier.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            return "[]"
        items = [
            {"id": f.id, "severity": f.severity, "category": f.category, "title": f.title,
             "where": [f"{e.path}:{e.line_start}" for e in f.evidence[:2]]}
            for f in dossier.findings[:25]
        ]
        return json.dumps(items, ensure_ascii=False)

    # ------------------------------------------------------------ stack
    def stack(self) -> StackReport:
        path = self.dir / STACK_FILE
        with _IO_LOCK:
            if path.is_file():
                try:
                    return StackReport.model_validate_json(path.read_text(encoding="utf-8"))
                except ValueError:
                    pass
        report = scan_stack(self.source)
        with _IO_LOCK:
            self.dir.mkdir(parents=True, exist_ok=True)
            path.write_text(report.model_dump_json(), encoding="utf-8")
        return report

    # ------------------------------------------------------------ validación de solicitudes
    def validate_request(self, request: AssessRequest) -> None:
        stack = self.stack()
        detected = {t.id for t in stack.technologies}
        if request.mode == "chosen":
            if not request.mappings:
                raise StudioStateError("Elige al menos una migración o pide a Bob que recomiende destinos.")
            seen: set[tuple[str, str | None]] = set()
            for mapping in request.mappings:
                if mapping.from_id not in detected:
                    raise StudioStateError(f"«{mapping.from_id}» no está entre las tecnologías detectadas.")
                if mapping.to_id not in {t.id for t in targets_for(mapping.from_id)}:
                    raise StudioStateError(f"«{mapping.to_id}» no es un destino posible para «{mapping.from_id}».")
                if (mapping.from_id, mapping.service) in seen:
                    raise StudioStateError(f"«{mapping.from_id}» aparece con dos destinos distintos.")
                seen.add((mapping.from_id, mapping.service))
        elif request.mappings:
            raise StudioStateError("En modo recomendación no se envían migraciones elegidas.")

    # ------------------------------------------------------------ transiciones (síncronas, rápidas)
    def begin_assess(self, request: AssessRequest) -> None:
        self.validate_request(request)
        self._begin(from_phases={"idle", "assessed", "planned", "implemented", "failed"}, to="assessing")
        self._update(request=request, assessment=None, plan=None, implementation=None, error=None)
        self._event("assessing", "Bob evalúa si conviene migrar y qué se sacrifica.")

    def begin_plan(self) -> None:
        state = self.state()
        if state.assessment is None or state.request is None:
            raise StudioStateError("Primero hay que evaluar la migración.")
        self._begin(from_phases={"assessed", "planned", "implemented", "failed"}, to="planning")
        self._update(plan=None, implementation=None, error=None)
        self._event("planning", "Bob prepara el plan detallado por pasos.")

    def begin_implement(self) -> None:
        state = self.state()
        if state.plan is None or state.request is None:
            raise StudioStateError("Primero hay que generar el plan.")
        self._begin(from_phases={"planned", "implemented", "failed"}, to="implementing")
        self._update(implementation=None, error=None)
        self._event("implementing", "Bob empieza a implementar el plan sobre una copia del proyecto.")

    def _begin(self, from_phases: set[str], to: Phase) -> None:
        state = self.state()
        if state.phase in {"assessing", "planning", "implementing"}:
            raise StudioBusyError("Ya hay una operación con Bob en curso para este análisis.")
        if state.phase not in from_phases:
            raise StudioStateError(f"No se puede pasar de «{state.phase}» a «{to}».")
        self._update(phase=to)

    # ------------------------------------------------------------ trabajo en segundo plano
    def _guard(self, fn: Callable[[], None]) -> None:
        if not _BOB_LOCK.acquire(blocking=False):
            self._update(phase="failed", error="Hay otra sesión de modernización con Bob en curso en el servidor.")
            return
        try:
            fn()
        except PlannerError as exc:
            logger.warning("Modernización %s: %s", self.job_dir.name, exc)
            self._event("failed", str(exc))
            self._update(phase="failed", error=redact_paths(str(exc)))
        except Exception:  # noqa: BLE001 - el worker nunca debe morir en silencio
            logger.exception("Error inesperado en la modernización %s", self.job_dir.name)
            self._update(phase="failed", error="Error interno inesperado; revisa los logs del servidor.")
        finally:
            _BOB_LOCK.release()

    def run_assess(self) -> None:
        def work() -> None:
            state = self.state()
            assert state.request is not None
            stack = self.stack()
            self._event("assessing", "Copiando el proyecto a un espacio de trabajo aislado")
            prepare_work(self.source, self.work)
            self._event("assessing", f"Stack medido enviado a Bob: {len(stack.technologies)} tecnologías, arquitectura {stack.architecture.kind}")
            assessment = planner.run_assessment(
                self.adapter_factory(self.work, "planner"), stack, state.request, self.work,
                findings=self.findings_digest(), sink=self._sink("assessing", "modernization-planner"),
                note=lambda message: self._event("assessing", message, kind="validator"),
            )
            self._event("assessed", f"Evaluación lista: veredicto {assessment.verdict}.")
            self._update(phase="assessed", assessment=assessment)

        self._guard(work)

    def run_plan(self) -> None:
        def work() -> None:
            state = self.state()
            assert state.request is not None and state.assessment is not None
            self._event("planning", "Copiando el proyecto a un espacio de trabajo aislado")
            prepare_work(self.source, self.work)
            plan = planner.run_plan(
                self.adapter_factory(self.work, "planner"), self.stack(), state.request, state.assessment, self.work,
                findings=self.findings_digest(), sink=self._sink("planning", "modernization-planner"),
                note=lambda message: self._event("planning", message, kind="validator"),
            )
            self._event("planned", f"Plan listo con {len(plan.steps)} pasos.")
            self._update(phase="planned", plan=plan)

        self._guard(work)

    def run_implement(self) -> None:
        def work() -> None:
            state = self.state()
            assert state.plan is not None and state.request is not None
            mappings = state.request.mappings or [Mapping(from_id=r.from_id, to_id=r.to_id) for r in (state.assessment.recommended if state.assessment else [])]
            mappings_text = json.dumps([m.model_dump() for m in mappings], ensure_ascii=False)
            # El adaptador apunta a la copia; run_implementation la prepara antes de la primera sesión.
            runner = self.adapter_factory(self.work, "surgeon")
            result = run_implementation(
                runner, state.plan, mappings_text, self.source, self.dir,
                root_name=f"{_slug(self.project_name)}-modernizado",
                on_event=lambda message, step: self._event("implementing", message, step),
                sink_for=lambda step: self._sink("implementing", "modernization-surgeon", step.id),
            )
            self._event("implemented", f"Migración lista: {result.files_changed} archivos cambiados.")
            self._update(phase="implemented", implementation=result)

        self._guard(work)


def _slug(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name.rsplit(".", 1)[0]).strip("-_")
    return cleaned[:40] or "proyecto"

