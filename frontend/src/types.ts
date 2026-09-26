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
  findings: Finding[];
  rejected_findings: Finding[];
  evidence_checks: EvidenceCheck[];
  stats: DossierStats;
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
