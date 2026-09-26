"""Contrato de datos v1 (D-01): expediente de hallazgos con evidencia por archivo y línea.

Fuente única del esquema: `contracts/schema-v1.json` se genera desde estos modelos
(`python -m app.contracts.export`). Bob produce `AuditorOutput`; el pipeline lo
valida y lo envuelve en `Dossier` con los números calculados por código (D7).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"

ExecutionMode = Literal["live", "imported", "example"]
Severity = Literal["critical", "high", "medium", "low"]
Category = Literal[
    "security",
    "maintainability",
    "business-rule",
    "data-integrity",
    "performance",
    "architecture",
    "testing",
]
Observation = Literal["observed", "inferred"]
EvidenceStatus = Literal["valid", "invalid"]


class Evidence(BaseModel):
    """Referencia verificable a un fragmento del repositorio analizado."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, description="Ruta relativa a la raíz del repo analizado.")
    line_start: int = Field(ge=1, description="Primera línea, 1-indexada.")
    line_end: int = Field(ge=1, description="Última línea, inclusiva.")
    snippet: str = Field(min_length=1, description="Fragmento literal presente en esas líneas.")

    @model_validator(mode="after")
    def _check_range(self) -> "Evidence":
        if self.line_end < self.line_start:
            raise ValueError("line_end no puede ser menor que line_start")
        return self


class Finding(BaseModel):
    """Hallazgo tal como lo emite Bob (evidence-auditor)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^F-\d+$")
    title: str = Field(min_length=3, max_length=160)
    category: Category
    subcategory: str = Field(min_length=1, max_length=60)
    severity: Severity
    observed_or_inferred: Observation
    evidence: list[Evidence] = Field(min_length=1)
    explanation: str = Field(min_length=10)
    recommendation: str = Field(min_length=5)


class AuditorOutput(BaseModel):
    """Salida esperada de Bob en modo evidence-auditor."""

    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]


class EvidenceCheck(BaseModel):
    """Resultado del validador determinista para una evidencia (etapa 3)."""

    finding_id: str
    evidence_index: int
    status: EvidenceStatus
    reason: str


class DossierStats(BaseModel):
    """Métricas calculadas por código, nunca por la IA (D7)."""

    findings_reported: int
    findings_validated: int
    evidence_total: int
    evidence_valid: int
    evidence_valid_ratio: float
    bob_cost: float | None = None
    bob_duration_ms: int | None = None


class RiskMetric(BaseModel):
    """Riesgo calculado con severidad y llamadores medidos en el grafo."""

    finding_id: str
    severity_weight: int = Field(ge=1, le=4)
    origin_functions: int = Field(ge=0)
    impacted_callers: int = Field(ge=0)
    score: int = Field(ge=1)
    formula: str


class PertEstimate(BaseModel):
    """Estimación del primer corte derivada solo de hechos medidos."""

    affected_routes: int = Field(ge=0)
    affected_functions: int = Field(ge=0)
    affected_lines: int = Field(ge=0)
    affected_complexity: int = Field(ge=0)
    optimistic_days: float = Field(gt=0)
    most_likely_days: float = Field(gt=0)
    pessimistic_days: float = Field(gt=0)
    expected_days: float = Field(gt=0)
    variance: float = Field(ge=0)
    formula: str
    assumptions: list[str]


class MigrationTestResult(BaseModel):
    name: str
    target: Literal["legacy", "modern"]
    status: Literal["passed", "failed", "not_run"]
    duration_ms: float = Field(ge=0)
    reason: str | None = None


class MigrationResult(BaseModel):
    status: Literal["passed", "failed", "not_run"]
    reason: str | None = None
    implementation_origin: str
    endpoint: str
    tests: list[MigrationTestResult] = Field(default_factory=list)
    legacy_file: str | None = None
    modern_file: str | None = None
    facade_file: str | None = None
    diff_file: str | None = None


class MigrationOption(BaseModel):
    """Opción de migración propuesta por el arquitecto (etapa migration-architect).

    No contiene cifras numéricas de días, riesgo ni radio: esos valores los calcula
    el código determinista (decision_metrics.py) y se leen del Dossier.
    Los pros y cons son texto cualitativo sin porcentajes ni estimaciones.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^OPT-\d+$", description="Identificador secuencial, p.ej. OPT-1.")
    name: str = Field(min_length=3, max_length=120)
    pattern: str = Field(min_length=3, max_length=120, description="Patrón de migración, p.ej. Strangler Fig.")
    finding_ids: list[str] = Field(
        min_length=1,
        description="IDs de hallazgos del ranking que justifican esta opción (deben existir en risk_matrix).",
    )
    pros: list[str] = Field(min_length=1)
    cons: list[str] = Field(min_length=1)
    recommended: bool = Field(description="True solo para la opción recomendada; exactamente una debe serlo.")


class Dossier(BaseModel):
    """Expediente técnico validado: salida de las etapas 2 y 3."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    execution_mode: ExecutionMode
    repo_name: str
    generated_at: str
    bob_task_id: str | None = None
    job_id: str | None = None
    source_sha256: str | None = None
    findings: list[Finding]
    rejected_findings: list[Finding] = Field(default_factory=list)
    evidence_checks: list[EvidenceCheck]
    stats: DossierStats
    risk_matrix: list[RiskMetric] = Field(default_factory=list)
    first_cut_pert: PertEstimate | None = None
    migration: MigrationResult | None = None
    migration_options: list[MigrationOption] = Field(default_factory=list)
