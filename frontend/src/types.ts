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
}

export interface Dossier {
  schema_version: string;
  execution_mode: ExecutionMode;
  repo_name: string;
  generated_at: string;
  bob_task_id: string | null;
  job_id: string | null;
  source_sha256: string | null;
  findings: Finding[];
  rejected_findings: Finding[];
  evidence_checks: EvidenceCheck[];
  stats: DossierStats;
  risk_matrix: {
    finding_id: string; severity_weight: number; origin_functions: number;
    impacted_callers: number; score: number; formula: string;
  }[];
  first_cut_pert: {
    affected_routes: number; affected_functions: number; affected_lines: number; affected_complexity: number;
    optimistic_days: number; most_likely_days: number; pessimistic_days: number;
    expected_days: number; variance: number; formula: string; assumptions: string[];
  } | null;
  migration: MigrationResult | null;
  /** Propuestas de Bob (migration-architect) validadas por código; vacío si no corrió o se rechazó. */
  migration_options?: {
    id: string; name: string; pattern: string; finding_ids: string[];
    pros: string[]; cons: string[]; recommended: boolean;
  }[];
}

export interface MigrationTestResult {
  name: string;
  target: "legacy" | "modern";
  status: "passed" | "failed" | "not_run";
  duration_ms: number;
  reason: string | null;
}

export interface MigrationResult {
  status: "passed" | "failed" | "not_run";
  reason: string | null;
  implementation_origin: string;
  endpoint: string;
  tests: MigrationTestResult[];
  legacy_file: string | null;
  modern_file: string | null;
  facade_file: string | null;
  diff_file: string | null;
}

export interface MigrationViewData {
  job_id: string;
  result: MigrationResult;
  legacy_code: string | null;
  modern_code: string | null;
  facade_code: string | null;
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

// --- Arquitectura medida sobre el código subido (GET /api/audits/{id}/architecture) ---------

export interface ArchitectureData {
  job_id: string;
  modules: { file: string; functions: number; findings: number; worst_severity: Severity | null }[];
  dependencies: { source: string; target: string; calls: number }[];
  mermaid: string | null;
  routes: { methods: string[]; rule: string; file: string; function: string; line_start: number }[];
  complex_functions: { file: string; name: string; line_start: number; complexity: number; rank: string; lines: number }[];
  circular_dependencies: string[][];
  tables: string[];
  sql: { total: number; concatenated: number; parameterized: number };
  totals: { files: number; functions: number; calls: number };
}

// Vista normalizada del avance de un análisis.
export interface FlowStage {
  id: string;
  number: number;
  label: string;
  detail: string;
  state: "pending" | "running" | "done" | "failed";
}

export interface FlowJob {
  id: string;
  label: string;
  execution_mode: ExecutionMode;
  status: "queued" | "running" | "done" | "failed";
  progress: number;
  current_stage: number;
  stages: FlowStage[];
  error: string | null;
  created_at: string;
  updated_at: string;
  /** "modernization": subido solo para el Estudio (sin auditoría, arquitectura ni expediente). */
  purpose: "audit" | "modernization";
}

// Grafo de llamadas real (GET /api/audits/{id}/graph).
export interface GraphNode {
  id: string; name: string; qualname: string; file: string; line_start: number; line_end: number;
  kind: "legacy" | "modern"; route: { rule: string; methods: string[] } | null;
}
export interface GraphFindingMark {
  finding_id: string; title: string; severity: string; status: string; node: string | null;
  path: string; line_start: number; line_end: number;
}
export interface GraphBlast {
  finding_id: string; severity: string; score: number | null; origin_nodes: string[]; impacted_nodes: string[]; unresolved_symbols: string[];
}
export interface GraphData {
  job_id: string;
  job_status: string;
  has_result: boolean;
  nodes: GraphNode[];
  edges: { source: string; target: string }[];
  findings: GraphFindingMark[];
  blast_radius: GraphBlast[];
  notes: string;
}

// --- Asistente contextual (POST /api/audits/{id}/ask) -------------------------------------

export type ContextKind = "project" | "finding" | "file" | "function" | "module";

export interface AskContext {
  kind: ContextKind;
  label?: string;
  finding_id?: string;
  path?: string;
  line_start?: number;
  line_end?: number;
}

export interface CodeRef {
  path: string;
  line_start: number;
  line_end: number;
  verified: boolean;
}

export interface Claim {
  text: string;
  refs: CodeRef[];
}

export interface AskAnswer {
  summary: string;
  facts: Claim[];
  inferences: Claim[];
  recommendations: Claim[];
  unknowns: string[];
  structured: boolean;
  bob_cost: number | null;
  bob_duration_ms: number | null;
}

// --- Actividad del análisis (GET /api/audits/{id}/events) ----------------------------------

export type StageId = "preparing" | "auditing" | "validating" | "migration" | "done";

export interface PipelineEvent {
  seq: number;
  t: number;
  stage: StageId;
  kind: string;
  actor: string;
  title: string;
  detail: string | null;
  data: Record<string, unknown>;
  recorded: boolean;
}

export interface ActivityPage {
  job_id: string;
  job_status: string;
  events: PipelineEvent[];
  next_after: number;
  has_more: boolean;
}


// --- Estudio de modernización (GET /api/audits/{id}/modernization) ---------------------------

export interface StackEvidence { path: string; line: number | null; text: string }
export interface DetectedTech {
  id: string; name: string; kind: string; language: string | null; icon: string | null; version: string | null;
  service: string | null; evidence: StackEvidence[];
}
export interface StackTarget { id: string; name: string; kind: string; language: string | null; icon: string | null }
export interface StackReport {
  languages: { id: string; name: string; files: number; lines: number; share: number }[];
  technologies: DetectedTech[];
  services: { name: string; path: string; technologies: string[]; dockerfile: boolean }[];
  architecture: { kind: "monolith" | "multi-app" | "microservices" | "unknown"; basis: string[] };
  targets: Record<string, StackTarget[]>;
  totals: { files: number; lines: number; technologies: number };
}

export type StudioPhase = "idle" | "assessing" | "assessed" | "planning" | "planned" | "implementing" | "implemented" | "failed";
export type Priority = "security" | "performance" | "cost" | "time" | "team" | "compatibility";
export interface StudioMapping { from_id: string; to_id: string; service?: string | null }
export interface AssessRequest { mode: "chosen" | "recommend"; mappings: StudioMapping[]; business_context: string; priorities: Priority[] }
export type Axis = "security" | "performance" | "cost" | "maintainability" | "compatibility" | "team" | "operations";
export interface Assessment {
  verdict: "recommended" | "conditional" | "not_recommended";
  summary: string; business_reading: string;
  tradeoffs: { axis: Axis; effect: "improves" | "worsens" | "neutral" | "depends"; detail: string; refs: { path: string; line_start: number; line_end: number; verified: boolean }[] }[];
  blockers: string[]; questions: string[];
  recommended: { from_id: string; to_id: string; why: string }[];
  bob_cost: number | null; bob_duration_ms: number | null;
}
export interface PlanStep {
  id: string; title: string; kind: string; why: string; depends_on: string[];
  files: { path: string; action: "modify" | "create" | "delete" }[];
  risk: "low" | "medium" | "high"; complexity: "low" | "medium" | "high"; validation: string; changes: string;
}
export interface MigrationPlan { summary: string; steps: PlanStep[]; rollback: string; bob_cost: number | null; bob_duration_ms: number | null }
export interface Implementation {
  steps: { step_id: string; status: "done" | "failed" | "skipped"; changed: { path: string; action: string }[]; outside_plan: string[]; note: string; bob_cost: number | null }[];
  checks: { path: string; kind: string; ok: boolean; detail: string }[];
  files_changed: number; lines_added: number; lines_removed: number; outside_plan: string[]; not_executed: string; bob_cost: number | null;
}
export interface StudioState {
  phase: StudioPhase; error: string | null; request: AssessRequest | null;
  assessment: Assessment | null; plan: MigrationPlan | null; implementation: Implementation | null;
  events: { t: number; phase: string; message: string; step_id: string | null }[];
  updated_at: string | null;
}
