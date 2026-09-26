"""Contratos del Estudio de modernización: solicitud, evaluación, plan, implementación y estado."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Verdict = Literal["recommended", "conditional", "not_recommended"]
Axis = Literal["security", "performance", "cost", "maintainability", "compatibility", "team", "operations"]
Effect = Literal["improves", "worsens", "neutral", "depends"]
Level = Literal["low", "medium", "high"]
StepKind = Literal["runtime", "dependencies", "code", "config", "data", "tests", "infra", "cutover"]
Phase = Literal["idle", "assessing", "assessed", "planning", "planned", "implementing", "implemented", "failed"]
Priority = Literal["security", "performance", "cost", "time", "team", "compatibility"]

MAX_MAPPINGS = 6


class Mapping(BaseModel):
    """Una migración elegida: tecnología actual -> tecnología destino."""

    model_config = ConfigDict(extra="forbid")

    from_id: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    to_id: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    service: str | None = Field(default=None, max_length=200)


class AssessRequest(BaseModel):
    """`chosen`: la persona eligió destinos. `recommend`: Bob propone destinos entre los del catálogo."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["chosen", "recommend"] = "chosen"
    mappings: list[Mapping] = Field(default_factory=list, max_length=MAX_MAPPINGS)
    business_context: str = Field(default="", max_length=1500)
    priorities: list[Priority] = Field(default_factory=list, max_length=4)


class CodeRef(BaseModel):
    path: str = Field(min_length=1, max_length=300)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    verified: bool = False


class Tradeoff(BaseModel):
    axis: Axis
    effect: Effect
    detail: str = Field(min_length=10, max_length=700)
    refs: list[CodeRef] = Field(default_factory=list, max_length=4)


class Recommended(BaseModel):
    from_id: str
    to_id: str
    why: str = Field(min_length=10, max_length=500)


class Assessment(BaseModel):
    verdict: Verdict
    summary: str = Field(min_length=20, max_length=900)
    business_reading: str = Field(min_length=10, max_length=900)
    tradeoffs: list[Tradeoff] = Field(min_length=3, max_length=12)
    blockers: list[str] = Field(default_factory=list, max_length=6)
    questions: list[str] = Field(default_factory=list, max_length=5)
    recommended: list[Recommended] = Field(default_factory=list, max_length=MAX_MAPPINGS)
    bob_cost: float | None = None
    bob_duration_ms: int | None = None


class FileChange(BaseModel):
    path: str = Field(min_length=1, max_length=300)
    action: Literal["modify", "create", "delete"]


class Step(BaseModel):
    id: str = Field(pattern=r"^S\d{1,2}$")
    title: str = Field(min_length=3, max_length=140)
    kind: StepKind
    why: str = Field(min_length=10, max_length=600)
    depends_on: list[str] = Field(default_factory=list, max_length=8)
    files: list[FileChange] = Field(default_factory=list, max_length=30)
    risk: Level
    complexity: Level
    validation: str = Field(min_length=5, max_length=500)
    changes: str = Field(min_length=10, max_length=1200)


class Plan(BaseModel):
    summary: str = Field(min_length=20, max_length=900)
    steps: list[Step] = Field(min_length=1, max_length=20)
    rollback: str = Field(min_length=10, max_length=600)
    bob_cost: float | None = None
    bob_duration_ms: int | None = None


class StepRun(BaseModel):
    step_id: str
    status: Literal["done", "failed", "skipped"]
    changed: list[FileChange] = Field(default_factory=list)
    outside_plan: list[str] = Field(default_factory=list)
    note: str = ""
    bob_cost: float | None = None


class FileCheck(BaseModel):
    path: str
    kind: str  # python | json | yaml | toml
    ok: bool
    detail: str = ""


class Implementation(BaseModel):
    steps: list[StepRun]
    checks: list[FileCheck]
    files_changed: int
    lines_added: int
    lines_removed: int
    outside_plan: list[str]
    not_executed: str = "El código generado no se ejecutó ni se probó: se comprobó solo su sintaxis."
    bob_cost: float | None = None


class StudioEvent(BaseModel):
    t: float
    phase: str
    message: str
    step_id: str | None = None


class StudioState(BaseModel):
    phase: Phase = "idle"
    error: str | None = None
    request: AssessRequest | None = None
    assessment: Assessment | None = None
    plan: Plan | None = None
    implementation: Implementation | None = None
    events: list[StudioEvent] = Field(default_factory=list)
    updated_at: str | None = None
