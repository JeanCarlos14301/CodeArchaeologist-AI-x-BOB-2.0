import type { FlowJob, Job } from "../types";

/** Etapas reales de la auditoría (backend/app/pipeline/evidence_audit.py). */
const STAGES = [
  { id: "preparing", label: "Preparar sandbox", detail: "Extrae el ZIP con controles de seguridad y copia el código sin tests ni credenciales." },
  { id: "auditing", label: "Auditoría con IBM Bob", detail: "El modo evidence-auditor recorre el código y emite hallazgos con archivo y líneas." },
  { id: "validating", label: "Validar evidencia", detail: "Python comprueba que cada archivo, rango de líneas y fragmento existen de verdad." },
  { id: "done", label: "Expediente", detail: "Solo quedan los hallazgos cuya evidencia coincide con el código." },
] as const;

export function jobToFlow(job: Job): FlowJob {
  const done = job.status === "done";
  const failed = job.status === "failed";
  const index = STAGES.findIndex((stage) => stage.id === job.stage);
  const current = done ? STAGES.length : Math.max(index, 0);
  return {
    id: job.id,
    label: job.sample.replace(/^upload:/, ""),
    execution_mode: job.execution_mode,
    status: job.status,
    progress: Math.round((current / STAGES.length) * 100),
    current_stage: done ? STAGES.length : current + 1,
    stages: STAGES.map((stage, i) => ({
      id: stage.id,
      number: i + 1,
      label: stage.label,
      detail: stage.detail,
      state: i < current ? "done" : i === current && !done ? (failed ? "pending" : "running") : "pending",
    })),
    error: job.error,
    created_at: job.created_at,
    updated_at: job.updated_at,
  };
}

export function elapsedSeconds(flow: FlowJob): number {
  return Math.max(0, Math.round((Date.parse(flow.updated_at) - Date.parse(flow.created_at)) / 1000));
}
