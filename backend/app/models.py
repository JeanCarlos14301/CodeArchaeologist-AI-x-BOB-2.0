"""Pydantic v2 models of the extended DossierResult contract (source of `contracts/schema-v1.json`).

Defines Snapshots, Evidence, Findings, Architecture Options, the PERT plan,
Characterization Tests, the Strangler Fig migration and validations.
Task D-01 and decisions D1, D3, D5, D6, D7 and D8. The live product uses `app/contracts/schema_v1.py`.
"""

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class EvidenceLocation(BaseModel):
    """Verifiable physical location of evidence in the source code."""
    path: str = Field(..., description="Normalized relative path of the file in the repository")
    line_start: int = Field(..., ge=1, description="Start line (1-indexed)")
    line_end: int = Field(..., ge=1, description="End line (1-indexed)")
    fragment: str = Field(..., description="Exact text fragment of the code in the range")
    observed_or_inferred: Literal["observed", "inferred"] = Field(
        default="observed",
        description="Whether the evidence was observed directly in the code or inferred"
    )


class Finding(BaseModel):
    """Technical or business finding backed by physical evidence."""
    id: str = Field(..., description="Unique finding identifier (e.g. EF-1, F-01)")
    title: str = Field(..., description="Descriptive title of the finding")
    category: str = Field(
        ...,
        description="Taxonomic category (e.g. security/sql-injection, maintainability/large-function, business-rule/duplication)"
    )
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = Field(
        ..., description="Technical severity level"
    )
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ..., description="Analytical certainty level"
    )
    priority: Literal["P0", "P1", "P2"] = Field(
        ..., description="Attention priority by value/risk"
    )
    expected_detection: bool = Field(
        default=True,
        description="True for real findings; False for negative test controls"
    )
    evidence: List[EvidenceLocation] = Field(
        default_factory=list,
        description="List of physical citations in the source code"
    )
    explanation: str = Field(..., description="Technical explanation of the detected problem")
    verification_method: str = Field(
        ..., description="Deterministic method to reproduce and verify the finding"
    )
    blast_radius_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Systemic blast radius score computed on the graph (0 to 100)"
    )
    transitive_impacted_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols and functions affected transitively in cascade"
    )
    status: Literal["accepted", "rejected", "inferred"] = Field(
        default="accepted",
        description="Status assigned by the deterministic evidence validator"
    )


class ArchitectureOption(BaseModel):
    """Compared modernization architecture option."""
    id: str = Field(..., description="Option identifier (e.g. OPT-1, OPT-2)")
    name: str = Field(..., description="Name of the alternative")
    pattern: str = Field(..., description="Modernization pattern (e.g. Strangler Fig, Leaf Cut, Big Bang)")
    pros: List[str] = Field(default_factory=list, description="Key advantages")
    cons: List[str] = Field(default_factory=list, description="Disadvantages and risks")
    target_stack: str = Field(..., description="Target technology stack (e.g. FastAPI + SQLite/PostgreSQL)")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(..., description="Operational risk level")
    estimated_effort_days: float = Field(..., ge=0.0, description="Estimated effort in working days")
    recommended: bool = Field(default=False, description="True if it is the recommended option")


class MigrationPhase(BaseModel):
    """Migration plan phase with a PERT statistical estimate."""
    phase_number: int = Field(..., ge=1, description="Sequential phase number")
    name: str = Field(..., description="Phase name")
    description: str = Field(..., description="Scope and deliverables of the phase")
    optimistic_days: float = Field(..., ge=0.0, description="Optimistic scenario (O)")
    nominal_days: float = Field(..., ge=0.0, description="Most likely scenario (M)")
    pessimistic_days: float = Field(..., ge=0.0, description="Pessimistic scenario (P)")
    pert_expected_days: float = Field(..., ge=0.0, description="PERT expected duration: (O + 4M + P) / 6")
    pert_variance: float = Field(..., ge=0.0, description="PERT variance: ((P - O) / 6)^2")
    assumptions: List[str] = Field(default_factory=list, description="Explicit non-negotiable assumptions")
    prerequisites: List[str] = Field(default_factory=list, description="Required technical prerequisites")
    rollback_strategy: str = Field(..., description="Rollback strategy in case of contingency")


class CharacterizationTestCase(BaseModel):
    """Individual result of a characterization test."""
    name: str = Field(..., description="Test name (e.g. test_invoice_owner_access)")
    target_endpoint: str = Field(..., description="Endpoint under test (e.g. GET /invoices/{id})")
    test_type: str = Field(..., description="Test type (contract, security, business_rule)")
    status: Literal["PASS", "FAIL", "SKIPPED"] = Field(..., description="Test verdict")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if it failed")


class CharacterizationTestReport(BaseModel):
    """Report of the characterization test suite run in the sandbox."""
    total_tests: int = Field(..., ge=0)
    passed_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    target_endpoint: str
    test_cases: List[CharacterizationTestCase] = Field(default_factory=list)
    all_passed: bool = Field(...)


class MigrationSummary(BaseModel):
    """Summary of the first migration cut executed with Strangler Fig."""
    endpoint_migrated: str = Field(..., description="Extracted endpoint (e.g. GET /invoices/{id})")
    modern_code_files: List[str] = Field(..., description="Modern code files created in modern/")
    facade_router_file: str = Field(..., description="Strangler Fig facade router file")
    legacy_tests_verdict: Literal["PASS", "FAIL", "SKIPPED"] = Field(
        ..., description="Verdict of the characterization tests against the legacy code"
    )
    modern_tests_verdict: Literal["PASS", "FAIL", "SKIPPED"] = Field(
        ..., description="Verdict of the characterization tests against the modernized code"
    )
    repaired_count: int = Field(default=0, ge=0, description="Number of automatic repairs applied (max 1)")
    diff_patch: str = Field(..., description="Generated unified .diff patch")


class ValidationReport(BaseModel):
    """Report of the deterministic evidence validator."""
    total_references: int = Field(..., ge=0)
    valid_references: int = Field(..., ge=0)
    invalid_references: int = Field(..., ge=0)
    fidelity_ratio: float = Field(..., ge=0.0, le=1.0, description="Share of verified references (1.0 = 100%)")
    details: List[str] = Field(default_factory=list)


class SnapshotMetadata(BaseModel):
    """Metadata of the analyzed repository."""
    sample_id: str = Field(..., description="Sample identifier (e.g. facturaya-v1)")
    repo_name: str = Field(..., description="Repository name")
    snapshot_sha256: str = Field(..., description="SHA-256 hash of the repository content")
    total_files: int = Field(..., ge=0)
    total_loc: int = Field(..., ge=0)
    languages_detected: List[str] = Field(default_factory=list)
    entrypoints: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_mode: Literal["live", "imported", "example"] = Field(
        default="live",
        description="Execution mode of the diagnosis (rule D8)"
    )


class DossierResult(BaseModel):
    """Complete technical diagnosis and migration dossier (contract v1)."""
    model_config = ConfigDict(extra="ignore")

    schema_version: str = Field(default="1.0", description="Data contract version")
    job_id: str = Field(..., description="Unique identifier of the analysis job")
    snapshot: SnapshotMetadata
    findings: List[Finding] = Field(default_factory=list)
    architecture_options: List[ArchitectureOption] = Field(default_factory=list)
    selected_first_cut: str = Field(default="GET /invoices/{id}")
    pert_plan: List[MigrationPhase] = Field(default_factory=list)
    characterization_tests_legacy: Optional[CharacterizationTestReport] = None
    characterization_tests_modern: Optional[CharacterizationTestReport] = None
    migration_summary: Optional[MigrationSummary] = None
    validation_report: ValidationReport
    executive_summary: Optional[str] = None
    mermaid_er_diagram: Optional[str] = None
    mermaid_call_flow: Optional[str] = None
    execution_mode: Literal["live", "imported", "example"] = "live"


# Models for the REST API

class JobCreateRequest(BaseModel):
    """Request to start a repository analysis."""
    source_type: Literal["demo", "zip"] = Field(
        ..., description="Source: demo (FacturaYa v1) or zip (upload)"
    )
    repo_name: Optional[str] = Field(default=None, description="Optional descriptive name")


class JobProgressEvent(BaseModel):
    """Progress event in the pipeline timeline."""
    stage: int = Field(..., ge=0, le=11, description="Stage number (0 to 11)")
    stage_name: str = Field(..., description="Stage name")
    status: Literal["started", "running", "completed", "failed", "skipped"]
    duration_ms: int = Field(default=0, ge=0)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: str = Field(default="")


class JobStatusResponse(BaseModel):
    """Status and progress response of a job."""
    job_id: str
    status: Literal["queued", "running", "completed", "completed_with_warnings", "failed", "cancelled"]
    stage: int = Field(..., ge=0, le=11)
    stage_name: str
    progress_percent: int = Field(..., ge=0, le=100)
    source_type: str
    execution_mode: str
    events: List[JobProgressEvent] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class MigrateRequest(BaseModel):
    """Request to execute the first migration cut."""
    endpoint: str = Field(default="GET /invoices/{id}", description="Endpoint to migrate with Strangler Fig")
