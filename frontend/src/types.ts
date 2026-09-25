// Espejo de backend/app/contracts/schema_v1.py y de las respuestas de backend/app/api/routes.py.

export type ExecutionMode = "live" | "imported" | "example";
export type JobStatus = "queued" | "running" | "done" | "failed";
export type Severity = "critical" | "high" | "medium" | "low";

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

// --- Contratos PROVISIONALES (aún no definidos por Daniel) -------------------------------
// Arquitectura (E-05), migración (E-06) y descargas (E-07). Cuando se congele el contrato en
// contracts/, alinear estos tipos con schema_v1.py. Mientras tanto se alimentan con fixtures.

export interface MigrationOption {
  id: string;
  name: string;
  summary: string;
  pros: string[];
  cons: string[];
  risk: "low" | "medium" | "high";
  /** Horas PERT: el valor esperado lo calcula el código (src/lib/pert.ts), no la IA. */
  effort_hours: { optimistic: number; likely: number; pessimistic: number };
  recommended: boolean;
}

export interface ArchitectureView {
  execution_mode: ExecutionMode;
  current_mermaid: string;
  target_mermaid: string;
  options: MigrationOption[];
}

export type TestStatus = "passed" | "failed" | "not_run";

export interface MigrationTest {
  id: string;
  name: string;
  status: TestStatus;
  detail: string;
}

export interface MigrationView {
  execution_mode: ExecutionMode;
  slice_name: string;
  description: string;
  legacy: { path: string; code: string };
  modern: { path: string; code: string };
  tests: MigrationTest[];
}

export interface DownloadItem {
  id: string;
  label: string;
  description: string;
  filename: string;
  format: "DOCX" | "JSON" | "MD" | "ZIP";
  url: string | null;
}

export interface DownloadsView {
  execution_mode: ExecutionMode;
  items: DownloadItem[];
}
