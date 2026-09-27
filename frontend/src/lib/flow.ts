import type { FlowJob, Job } from "../types";

/** Real pipeline stages (backend/app/pipeline/evidence_audit.py), in product language. */
const STAGES = [
  { id: "preparing", label: "Repository indexed", running: "Indexing repository", detail: "Safe extraction into a sandbox; the code never runs." },
  { id: "auditing", label: "IBM Bob audit", running: "Bob analyzes the code", detail: "evidence-auditor walks the code and delegates to specialized subagents." },
  { id: "validating", label: "Evidence verified", running: "Verifying evidence", detail: "Python checks the file, lines and snippet of every finding." },
  { id: "migration", label: "First cut tested", running: "Testing the first cut", detail: "Characterization tests against the legacy code and the modern cut (registered samples only)." },
  { id: "done", label: "Dossier ready", running: "Generating the dossier", detail: "Only findings whose evidence matches the code remain." },
] as const;

export function jobToFlow(job: Job): FlowJob {
  const done = job.status === "done";
  const failed = job.status === "failed";
  const index = STAGES.findIndex((stage) => stage.id === job.stage);
  const current = done ? STAGES.length : Math.max(index, 0);
  return {
    id: job.id,
    purpose: job.sample.startsWith("modernize:") ? "modernization" : "audit",
    label: job.sample.replace(/^(upload|modernize):/, ""),
    execution_mode: job.execution_mode,
    status: job.status,
    progress: Math.round((current / STAGES.length) * 100),
    current_stage: done ? STAGES.length : current + 1,
    stages: STAGES.map((stage, i) => ({
      id: stage.id,
      number: i + 1,
      label: i === current && !done && !failed ? stage.running : stage.label,
      detail: stage.detail,
      state: i < current ? "done" : i === current && !done ? (failed ? "failed" : "running") : "pending",
    })),
    error: job.error,
    created_at: job.created_at,
    updated_at: job.updated_at,
  };
}

export const isActive = (job: { status: string } | null | undefined) => job?.status === "queued" || job?.status === "running";

export function statusLabel(flow: FlowJob): string {
  if (flow.status === "queued") return "Queued";
  if (flow.status === "failed") return "Analysis failed";
  if (flow.status === "done") return "Analysis complete";
  return flow.stages.find((stage) => stage.state === "running")?.label ?? "Analyzing";
}

export function elapsedSeconds(flow: FlowJob): number {
  return Math.max(0, Math.round((Date.parse(flow.updated_at) - Date.parse(flow.created_at)) / 1000));
}
