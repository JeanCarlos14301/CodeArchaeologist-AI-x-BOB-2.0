"""Data contract v1 (D-01): dossier of findings with evidence by file and line.

These models are what the live product uses. Bob produces `AuditorOutput`; the pipeline
validates it and wraps it in `Dossier` with the numbers computed by code (D7).
`python -m app.contracts.export` writes this contract as JSON Schema.
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
    """Verifiable reference to a snippet of the analyzed repository."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, description="Path relative to the root of the analyzed repo.")
    line_start: int = Field(ge=1, description="First line, 1-indexed.")
    line_end: int = Field(ge=1, description="Last line, inclusive.")
    snippet: str = Field(min_length=1, description="Verbatim snippet present in those lines.")

    @model_validator(mode="after")
    def _check_range(self) -> "Evidence":
        if self.line_end < self.line_start:
            raise ValueError("line_end cannot be smaller than line_start")
        return self


class Finding(BaseModel):
    """Finding as Bob (evidence-auditor) emits it."""

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
    """Expected output of Bob in evidence-auditor mode."""

    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]


class EvidenceCheck(BaseModel):
    """Result of the deterministic validator for one piece of evidence."""

    finding_id: str
    evidence_index: int
    status: EvidenceStatus
    reason: str


class DossierStats(BaseModel):
    """Metrics computed by code, never by the AI (D7)."""

    findings_reported: int
    findings_validated: int
    evidence_total: int
    evidence_valid: int
    evidence_valid_ratio: float
    bob_cost: float | None = None
    bob_duration_ms: int | None = None


class RiskMetric(BaseModel):
    """Risk computed from severity and the callers measured on the graph."""

    finding_id: str
    severity_weight: int = Field(ge=1, le=4)
    origin_functions: int = Field(ge=0)
    impacted_callers: int = Field(ge=0)
    score: int = Field(ge=1)
    formula: str


class PertEstimate(BaseModel):
    """First-cut estimate derived only from measured facts."""

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
    """Migration option proposed by the architect (migration-architect stage).

    Each option describes a candidate route from the deterministic ranking (migration_ranking.py).
    It contains no numeric figures for days, risk or radius: those values are computed by
    deterministic code and read from the Dossier.
    Pros and cons are qualitative text with no percentages or estimates.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^OPT-\d+$", description="Sequential identifier, e.g. OPT-1.")
    name: str = Field(min_length=3, max_length=120)
    pattern: str = Field(min_length=3, max_length=120, description="Migration pattern, e.g. Strangler Fig.")
    endpoint: str | None = Field(
        default=None,
        max_length=200,
        description="Endpoint of the ranking candidate this option describes, copied verbatim.",
    )
    finding_ids: list[str] = Field(
        default_factory=list,
        description="IDs of the findings that candidate mitigates according to the engine (may be empty).",
    )
    pros: list[str] = Field(min_length=1)
    cons: list[str] = Field(min_length=1)
    recommended: bool = Field(description="True only for the recommended option; exactly one must be.")


class RouteCandidate(BaseModel):
    """Flask route candidate for a Strangler Fig migration (deterministic assessment A)."""

    endpoint: str = Field(description="Method and rule, e.g. 'GET /invoices/{id}'.")
    http_methods: list[str]
    rule: str
    function_name: str
    file_path: str
    line_start: int
    line_end: int
    value: float = Field(ge=1.0)
    risk: float = Field(gt=0.0)
    testability: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0)
    formula: str
    findings_mitigated: list[str] = Field(default_factory=list)
    shared_functions: int = 0
    tables_written: list[str] = Field(default_factory=list)
    complexity: int = 0
    lines: int = 0
    in_circular_dependency: bool = False
    touches_business_data: bool = Field(
        default=True,
        description="Its scope reads or writes some table; otherwise its score is weighted by half (D3: visible to the business).",
    )
    why: str = ""


class MigrationWave(BaseModel):
    """Wave in the Strangler Fig roadmap with its own computed PERT."""

    wave_number: int = Field(ge=1)
    name: str
    description: str
    candidates: list[RouteCandidate] = Field(default_factory=list)
    pert: PertEstimate | None = None


class MigrationRecommendation(BaseModel):
    """Complete deterministic migration recommendation, by cut and by waves."""

    recommended: RouteCandidate | None = None
    alternatives: list[RouteCandidate] = Field(default_factory=list)
    do_not_start_here: RouteCandidate | None = None
    candidates: list[RouteCandidate] = Field(default_factory=list)
    waves: list[MigrationWave] = Field(default_factory=list)
    first_cut_pert: PertEstimate | None = None
    reference_comparison: str | None = None


class Dossier(BaseModel):
    """Validated technical dossier: output of the audit pipeline."""

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
    recommendation: MigrationRecommendation | None = None

