"""Modelos Pydantic v2 y única fuente de verdad para el contrato de datos v1.

Define la estructura de Snapshots, Evidencias, Hallazgos, Opciones Arquitectónicas,
Plan PERT, Pruebas de Caracterización, Migración Strangler Fig y validaciones.
Cumple con la tarea D-01 y las decisiones D1, D3, D5, D6, D7 y D8.
"""

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class EvidenceLocation(BaseModel):
    """Ubicación física comprobable de evidencia en el código fuente."""
    path: str = Field(..., description="Ruta relativa normalizada del archivo en el repositorio")
    line_start: int = Field(..., ge=1, description="Línea inicial (1-indexed)")
    line_end: int = Field(..., ge=1, description="Línea final (1-indexed)")
    fragment: str = Field(..., description="Fragmento textual exacto del código en el rango")
    observed_or_inferred: Literal["observed", "inferred"] = Field(
        default="observed",
        description="Indica si la evidencia fue observada directamente en código o inferida"
    )


class Finding(BaseModel):
    """Hallazgo técnico o de negocio respaldado por evidencia física."""
    id: str = Field(..., description="Identificador único del hallazgo (ej. EF-1, F-01)")
    title: str = Field(..., description="Título descriptivo del hallazgo")
    category: str = Field(
        ...,
        description="Categoría taxonómica (ej. security/sql-injection, maintainability/large-function, business-rule/duplication)"
    )
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = Field(
        ..., description="Nivel de severidad técnica"
    )
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ..., description="Nivel de certidumbre analítica"
    )
    priority: Literal["P0", "P1", "P2"] = Field(
        ..., description="Prioridad de atención según valor/riesgo"
    )
    expected_detection: bool = Field(
        default=True,
        description="True para hallazgos reales; False para controles negativos de prueba"
    )
    evidence: List[EvidenceLocation] = Field(
        default_factory=list,
        description="Lista de citas físicas en código fuente"
    )
    explanation: str = Field(..., description="Explicación técnica del problema detectado")
    verification_method: str = Field(
        ..., description="Método determinista para reproducir y comprobar el hallazgo"
    )
    blast_radius_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Puntaje de radio de explosión sistémico calculado por grafo (0 a 100)"
    )
    transitive_impacted_symbols: List[str] = Field(
        default_factory=list,
        description="Símbolos y funciones en cascada afectados transitivamente"
    )
    status: Literal["accepted", "rejected", "inferred"] = Field(
        default="accepted",
        description="Estado asignado por el validador determinista de evidencia"
    )


class ArchitectureOption(BaseModel):
    """Opción arquitectónica de modernización comparada."""
    id: str = Field(..., description="Identificador de la opción (ej. OPT-1, OPT-2)")
    name: str = Field(..., description="Nombre de la alternativa")
    pattern: str = Field(..., description="Patrón de modernización (ej. Strangler Fig, Leaf Cut, Big Bang)")
    pros: List[str] = Field(default_factory=list, description="Ventajas clave")
    cons: List[str] = Field(default_factory=list, description="Desventajas y riesgos")
    target_stack: str = Field(..., description="Stack tecnológico de destino (ej. FastAPI + SQLite/PostgreSQL)")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(..., description="Nivel de riesgo operativo")
    estimated_effort_days: float = Field(..., ge=0.0, description="Esfuerzo estimado en días hábiles")
    recommended: bool = Field(default=False, description="True si es la opción recomendada")


class MigrationPhase(BaseModel):
    """Fase del plan de migración con estimación estadística PERT."""
    phase_number: int = Field(..., ge=1, description="Número secuencial de fase")
    name: str = Field(..., description="Nombre de la fase")
    description: str = Field(..., description="Alcance y entregables de la fase")
    optimistic_days: float = Field(..., ge=0.0, description="Escenario optimista (O)")
    nominal_days: float = Field(..., ge=0.0, description="Escenario más probable (M)")
    pessimistic_days: float = Field(..., ge=0.0, description="Escenario pesimista (P)")
    pert_expected_days: float = Field(..., ge=0.0, description="Duración esperada PERT: (O + 4M + P) / 6")
    pert_variance: float = Field(..., ge=0.0, description="Varianza PERT: ((P - O) / 6)^2")
    assumptions: List[str] = Field(default_factory=list, description="Supuestos explícitos no negociables")
    prerequisites: List[str] = Field(default_factory=list, description="Prerrequisitos técnicos requeridos")
    rollback_strategy: str = Field(..., description="Estrategia de marcha atrás en caso de contingencia")


class CharacterizationTestCase(BaseModel):
    """Resultado individual de una prueba de caracterización."""
    name: str = Field(..., description="Nombre del test (ej. test_invoice_owner_access)")
    target_endpoint: str = Field(..., description="Endpoint evaluado (ej. GET /invoices/{id})")
    test_type: str = Field(..., description="Tipo de prueba (contract, security, business_rule)")
    status: Literal["PASS", "FAIL", "SKIPPED"] = Field(..., description="Veredicto de la prueba")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duración en milisegundos")
    error_message: Optional[str] = Field(default=None, description="Mensaje de error si falló")


class CharacterizationTestReport(BaseModel):
    """Reporte de la suite de pruebas de caracterización ejecutada en sandbox."""
    total_tests: int = Field(..., ge=0)
    passed_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    target_endpoint: str
    test_cases: List[CharacterizationTestCase] = Field(default_factory=list)
    all_passed: bool = Field(...)


class MigrationSummary(BaseModel):
    """Resumen del primer corte de migración ejecutado con Strangler Fig."""
    endpoint_migrated: str = Field(..., description="Endpoint extraído (ej. GET /invoices/{id})")
    modern_code_files: List[str] = Field(..., description="Archivos de código moderno creados en modern/")
    facade_router_file: str = Field(..., description="Archivo de enrutador fachada Strangler Fig")
    legacy_tests_verdict: Literal["PASS", "FAIL", "SKIPPED"] = Field(
        ..., description="Veredicto de las pruebas de caracterización contra el código legado"
    )
    modern_tests_verdict: Literal["PASS", "FAIL", "SKIPPED"] = Field(
        ..., description="Veredicto de las pruebas de caracterización contra el código modernizado"
    )
    repaired_count: int = Field(default=0, ge=0, description="Número de reparaciones automáticas aplicadas (máx. 1)")
    diff_patch: str = Field(..., description="Parche unificado .diff generado")


class ValidationReport(BaseModel):
    """Reporte del validador determinista de evidencia."""
    total_references: int = Field(..., ge=0)
    valid_references: int = Field(..., ge=0)
    invalid_references: int = Field(..., ge=0)
    fidelity_ratio: float = Field(..., ge=0.0, le=1.0, description="Tasa de referencias verificadas (1.0 = 100%)")
    details: List[str] = Field(default_factory=list)


class SnapshotMetadata(BaseModel):
    """Metadatos del repositorio analizado."""
    sample_id: str = Field(..., description="Identificador de la muestra (ej. facturaya-v1)")
    repo_name: str = Field(..., description="Nombre del repositorio")
    snapshot_sha256: str = Field(..., description="Hash SHA-256 del contenido del repositorio")
    total_files: int = Field(..., ge=0)
    total_loc: int = Field(..., ge=0)
    languages_detected: List[str] = Field(default_factory=list)
    entrypoints: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_mode: Literal["live", "imported", "example"] = Field(
        default="live",
        description="Modo de ejecución del diagnóstico (regla D8)"
    )


class DossierResult(BaseModel):
    """Expediente técnico completo de diagnóstico y migración (Contrato v1)."""
    model_config = ConfigDict(extra="ignore")

    schema_version: str = Field(default="1.0", description="Versión del contrato de datos")
    job_id: str = Field(..., description="Identificador único del job de análisis")
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


# Modelos para la API REST

class JobCreateRequest(BaseModel):
    """Solicitud para iniciar un análisis de repositorio."""
    source_type: Literal["demo", "zip"] = Field(
        ..., description="Origen: demo (FacturaYa v1) o zip (subida)"
    )
    repo_name: Optional[str] = Field(default=None, description="Nombre descriptivo opcional")


class JobProgressEvent(BaseModel):
    """Evento de avance en la línea de tiempo del pipeline."""
    stage: int = Field(..., ge=0, le=11, description="Número de etapa (0 a 11)")
    stage_name: str = Field(..., description="Nombre de la etapa")
    status: Literal["started", "running", "completed", "failed", "skipped"]
    duration_ms: int = Field(default=0, ge=0)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: str = Field(default="")


class JobStatusResponse(BaseModel):
    """Respuesta de estado y progreso de un job."""
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
    """Solicitud para ejecutar el primer corte de migración."""
    endpoint: str = Field(default="GET /invoices/{id}", description="Endpoint a migrar con Strangler Fig")
