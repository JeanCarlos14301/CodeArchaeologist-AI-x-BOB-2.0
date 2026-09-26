// Espejo de backend/app/contracts/schema_v1.py y de las respuestas de backend/app/api/routes.py.

export type ExecutionMode = "live" | "imported" | "example";
export type JobStatus = "queued" | "running" | "done" | "failed";
export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface Evidence {
  path: string;
  line_start: number;
  line_end: number;
  snippet: string;
}

export interface Finding {
  id: string;
  title: string;
  category: string;
  subcategory: string;
  severity: Severity;
  observed_or_inferred: "observed" | "inferred";
  evidence: Evidence[];
  explanation: string;
  recommendation: string;
  // Solo los aporta el motor /api/jobs (DossierResult).
  confidence?: "HIGH" | "MEDIUM" | "LOW";
  priority?: string;
  blast_radius_score?: number;
  verification_method?: string;
  impacted_symbols?: string[];
}

export interface EvidenceCheck {
  finding_id: string;
  evidence_index: number;
  status: "valid" | "invalid";
  reason: string;
}

export interface DossierStats {
  findings_reported: number;
  findings_validated: number;
  evidence_total: number;
  evidence_valid: number;
  evidence_valid_ratio: number;
  bob_cost: number | null;
  bob_duration_ms: number | null;
  /** Suma de la duración de las etapas del pipeline (motor /api/jobs). */
  pipeline_ms?: number | null;
}

export interface Dossier {
  schema_version: string;
  execution_mode: ExecutionMode;
  repo_name: string;
  generated_at: string;
  bob_task_id: string | null;
  findings: Finding[];
  rejected_findings: Finding[];
  evidence_checks: EvidenceCheck[];
  stats: DossierStats;
  // Solo con el motor /api/jobs.
  executive_summary?: string | null;
  snapshot?: { total_files: number; total_loc: number; languages: string[]; sha256: string };
}

export interface Job {
  id: string;
  sample: string;
  execution_mode: ExecutionMode;
  status: JobStatus;
  stage: string;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditDetail {
  job: Job;
  dossier: Dossier | null;
}

export interface BobStatus {
  installed: boolean;
  version: string | null;
  api_key_configured: boolean;
  custom_modes: string[];
  subagents: string[];
  skills: string[];
  max_cost_per_run: number;
  timeout_s: number;
  live_requires_token: boolean;
}

export interface SampleInfo {
  id: string;
  name: string;
}

export interface SourceExcerpt {
  path: string;
  start: number;
  end: number;
  total_lines: number;
  lines: { number: number; text: string }[];
}

// --- Vistas derivadas ---------------------------------------------------------------------
// Arquitectura, migración y descargas. Con el motor /api/jobs se derivan del DossierResult real
// (src/lib/jobsAdapter.ts); con el motor /api/audits o sin backend se usan fixtures de ejemplo.

export interface Diagram {
  id: string;
  label: string;
  mermaid: string;
  /** "observed": sale del código; "inferred": es el plan objetivo derivado del corte de migración. */
  provenance: "observed" | "inferred";
}

export interface ArchOption {
  id: string;
  name: string;
  pattern: string | null;
  target_stack: string | null;
  pros: string[];
  cons: string[];
  risk: "low" | "medium" | "high";
  effort_days: number;
  recommended: boolean;
}

export interface PertPhase {
  phase_number: number;
  name: string;
  description: string;
  optimistic_days: number;
  nominal_days: number;
  pessimistic_days: number;
  rollback_strategy: string;
}

export interface ArchitectureView {
  execution_mode: ExecutionMode;
  diagrams: Diagram[];
  options: ArchOption[];
  pert_plan: PertPhase[];
  selected_first_cut: string | null;
}

export type TestStatus = "passed" | "failed" | "not_run";

export interface MigrationTest {
  id: string;
  name: string;
  status: TestStatus;
  detail: string;
  suite: "legacy" | "modern";
}

export interface CodeSlice {
  path: string;
  code: string;
  line_start: number;
}

export interface MigrationView {
  execution_mode: ExecutionMode;
  slice_name: string;
  description: string;
  legacy: CodeSlice | null;
  modern: CodeSlice | null;
  tests: MigrationTest[];
  diff: { added: number; removed: number } | null;
  legacy_verdict: string | null;
  modern_verdict: string | null;
}

export interface DownloadItem {
  id: string;
  label: string;
  description: string;
  filename: string;
  format: "DOCX" | "JSON" | "MD" | "ZIP" | "HTML" | "PPTX" | "DIFF";
  url: string | null;
}

export interface DownloadsView {
  execution_mode: ExecutionMode;
  items: DownloadItem[];
}

// --- Motor /api/jobs (Daniel): pipeline de 11 etapas ---------------------------------------

export type EngineId = "jobs" | "audits";

export interface JobEventRaw {
  stage: number;
  stage_name: string;
  status: "started" | "running" | "completed" | "failed" | "skipped";
  duration_ms: number;
  timestamp: string;
  message: string;
}

export interface JobStatusRaw {
  job_id: string;
  status: "queued" | "running" | "completed" | "completed_with_warnings" | "failed" | "cancelled";
  stage: number;
  stage_name: string;
  progress_percent: number;
  source_type: string;
  execution_mode: string;
  events: JobEventRaw[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DossierResultRaw {
  job_id: string;
  snapshot: { sample_id: string; repo_name: string; snapshot_sha256: string; total_files: number; total_loc: number; languages_detected: string[]; entrypoints: string[]; timestamp: string; execution_mode: ExecutionMode };
  findings: {
    id: string; title: string; category: string; severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
    confidence: "HIGH" | "MEDIUM" | "LOW"; priority: string; explanation: string; verification_method: string;
    blast_radius_score: number; transitive_impacted_symbols: string[]; status: "accepted" | "rejected" | "inferred";
    evidence: { path: string; line_start: number; line_end: number; fragment: string; observed_or_inferred: "observed" | "inferred" }[];
  }[];
  architecture_options: {
    id: string; name: string; pattern: string; pros: string[]; cons: string[]; target_stack: string;
    risk_level: "LOW" | "MEDIUM" | "HIGH"; estimated_effort_days: number; recommended: boolean;
  }[];
  selected_first_cut: string;
  pert_plan: {
    phase_number: number; name: string; description: string; optimistic_days: number; nominal_days: number;
    pessimistic_days: number; pert_expected_days: number; pert_variance: number; rollback_strategy: string;
  }[];
  characterization_tests_legacy: TestReportRaw | null;
  characterization_tests_modern: TestReportRaw | null;
  migration_summary: { endpoint_migrated: string; modern_code_files: string[]; facade_router_file: string; legacy_tests_verdict: string; modern_tests_verdict: string; repaired_count: number; diff_patch: string } | null;
  validation_report: { total_references: number; valid_references: number; invalid_references: number; fidelity_ratio: number; details: string[] };
  executive_summary: string | null;
  mermaid_er_diagram: string | null;
  mermaid_call_flow: string | null;
  execution_mode: ExecutionMode;
}

export interface TestReportRaw {
  total_tests: number; passed_count: number; failed_count: number; target_endpoint: string; all_passed: boolean;
  test_cases: { name: string; target_endpoint: string; test_type: string; status: "PASS" | "FAIL" | "SKIPPED"; duration_ms: number; error_message: string | null }[];
}

// Vista normalizada del avance de un análisis (misma forma para ambos motores).
export interface FlowStage {
  id: string;
  number: number;
  label: string;
  state: "pending" | "running" | "done" | "failed";
  duration_ms: number | null;
  message: string | null;
}

export interface FlowJob {
  id: string;
  engine: EngineId;
  label: string;
  execution_mode: ExecutionMode;
  status: "queued" | "running" | "done" | "failed";
  progress: number;
  current_stage: number;
  stages: FlowStage[];
  error: string | null;
  created_at: string;
  updated_at: string;
}

// Grafo de llamadas real (GET /api/jobs/{id}/graph).
export interface GraphNode {
  id: string; name: string; qualname: string; file: string; line_start: number; line_end: number;
  kind: "legacy" | "modern"; route: { rule: string; methods: string[] } | null;
}
export interface GraphFindingMark {
  finding_id: string; title: string; severity: string; status: string; node: string | null;
  path: string; line_start: number; line_end: number;
}
export interface GraphBlast {
  finding_id: string; severity: string; score: number; origin_nodes: string[]; impacted_nodes: string[]; unresolved_symbols: string[];
}
export interface GraphData {
  job_id: string;
  job_status: string;
  has_result: boolean;
  nodes: GraphNode[];
  edges: { source: string; target: string }[];
  findings: GraphFindingMark[];
  blast_radius: GraphBlast[];
  migration_cut: {
    endpoint: string; legacy_node: string | null; modern_nodes: string[]; modern_files: string[];
    diff_added: number; diff_removed: number; legacy_tests_verdict: string | null; modern_tests_verdict: string | null;
  } | null;
  notes: string;
}
