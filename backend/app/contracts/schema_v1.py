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


class Dossier(BaseModel):
    """Expediente técnico validado: salida de las etapas 2 y 3."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    execution_mode: ExecutionMode
    repo_name: str
    generated_at: str
    bob_task_id: str | None = None
    findings: list[Finding]
    rejected_findings: list[Finding] = Field(default_factory=list)
    evidence_checks: list[EvidenceCheck]
    stats: DossierStats
