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
