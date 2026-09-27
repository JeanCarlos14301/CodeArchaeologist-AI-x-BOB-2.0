// Mirror of backend/app/contracts/schema_v1.py and of the responses of backend/app/api/routes.py.

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
  first_cut_pert: PertEstimate | null;
  migration: MigrationResult | null;
  /** Bob's proposals (migration-architect) over the route ranking, validated by code; empty if it did not run or was rejected. */
  migration_options?: {
    id: string; name: string; pattern: string; endpoint?: string | null; finding_ids: string[];
    pros: string[]; cons: string[]; recommended: boolean;
  }[];
  /** Deterministic route ranking (backend/app/pipeline/migration_ranking.py): what to migrate first and in which waves. */
  recommendation?: MigrationRecommendation | null;
}

export interface PertEstimate {
  affected_routes: number; affected_functions: number; affected_lines: number; affected_complexity: number;
  optimistic_days: number; most_likely_days: number; pessimistic_days: number;
  expected_days: number; variance: number; formula: string; assumptions: string[];
}

export interface RouteCandidate {
  endpoint: string;
  http_methods: string[];
  rule: string;
  function_name: string;
  file_path: string;
  line_start: number;
  line_end: number;
  value: number;
  risk: number;
  testability: number;
  score: number;
  formula: string;
  findings_mitigated: string[];
  shared_functions: number;
  tables_written: string[];
  complexity: number;
  lines: number;
  in_circular_dependency: boolean;
  /** Absent in dossiers produced before the business-data factor existed. */
  touches_business_data?: boolean;
  why: string;
}

export interface MigrationWave {
  wave_number: number;
  name: string;
  description: string;
  candidates: RouteCandidate[];
  pert: PertEstimate | null;
}

export interface MigrationRecommendation {
  recommended: RouteCandidate | null;
  alternatives: RouteCandidate[];
  do_not_start_here: RouteCandidate | null;
  candidates: RouteCandidate[];
  waves: MigrationWave[];
  first_cut_pert: PertEstimate | null;
  reference_comparison: string | null;
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
  /** BOB_DAILY_SPEND_LIMIT in bobcoins; null when the server has no daily guard. */
  daily_spend_limit?: number | null;
  spent_today?: number;
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

// --- Architecture measured on the uploaded code (GET /api/audits/{id}/architecture) --------

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

// Normalized view of an analysis's progress.
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
  /** "modernization": uploaded only for the Studio (no audit, architecture or dossier). */
  purpose: "audit" | "modernization";
}

// Real call graph (GET /api/audits/{id}/graph).
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

// --- Contextual assistant (POST /api/audits/{id}/ask) -------------------------------------

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

/** A real Bob action while it answers a question (from the Bob stream, with no file contents). */
export interface AskStep {
  seq: number;
  /** Seconds since Bob started answering. */
  t: number;
  kind: string;
  message: string;
  detail: string | null;
  data: Record<string, string | number | null>;
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
  /** What Bob did to reach the answer. */
  activity: AskStep[];
}

// --- Analysis activity (GET /api/audits/{id}/events) ---------------------------------------

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


// --- Modernization Studio (GET /api/audits/{id}/modernization) ------------------------------

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
export interface StudioAnswer { question: string; answer: string }
export interface AssessRequest {
  mode: "chosen" | "recommend"; mappings: StudioMapping[]; business_context: string; priorities: Priority[];
  /** The person's answers to the questions Bob left open. */
  answers?: StudioAnswer[];
}
export type Axis = "security" | "performance" | "cost" | "maintainability" | "compatibility" | "team" | "operations";
export interface Assessment {
  verdict: "recommended" | "conditional" | "not_recommended";
  summary: string; business_reading: string;
  tradeoffs: { axis: Axis; effect: "improves" | "worsens" | "neutral" | "depends"; detail: string; refs: { path: string; line_start: number; line_end: number; verified: boolean }[] }[];
  blockers: string[]; questions: string[]; fixes_during_migration: string[];
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
  steps: { step_id: string; status: "done" | "failed" | "skipped"; changed: { path: string; action: string }[]; outside_plan: string[]; note: string; fixed: string[]; bob_cost: number | null }[];
  checks: { path: string; kind: string; ok: boolean; detail: string }[];
  files_changed: number; lines_added: number; lines_removed: number; outside_plan: string[]; not_executed: string; bob_cost: number | null;
}
export interface StudioState {
  phase: StudioPhase; error: string | null; request: AssessRequest | null;
  assessment: Assessment | null; plan: MigrationPlan | null; implementation: Implementation | null;
  events: {
    t: number; phase: string; message: string; step_id: string | null; kind: string; actor: string | null;
    detail: string | null; data: Record<string, string | number | null>;
  }[];
  updated_at: string | null;
}
