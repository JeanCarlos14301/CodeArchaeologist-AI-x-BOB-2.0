import type { FlowJob, Job } from "../types";

/** Etapas reales del pipeline (backend/app/pipeline/evidence_audit.py), con lenguaje de producto. */
const STAGES = [
  { id: "preparing", label: "Repositorio indexado", running: "Indexando repositorio", detail: "Extracción segura en un sandbox; el código nunca se ejecuta." },
  { id: "auditing", label: "Auditoría de IBM Bob", running: "Bob analiza el código", detail: "evidence-auditor recorre el código y delega en subagentes especializados." },
  { id: "validating", label: "Evidencia verificada", running: "Verificando evidencia", detail: "Python comprueba archivo, líneas y fragmento de cada hallazgo." },
  { id: "migration", label: "Primer corte probado", running: "Probando primer corte", detail: "Pruebas de caracterización contra el legado y el corte moderno (solo muestras registradas)." },
  { id: "done", label: "Expediente listo", running: "Generando expediente", detail: "Solo quedan hallazgos cuya evidencia coincide con el código." },
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
  if (flow.status === "queued") return "En cola";
  if (flow.status === "failed") return "Análisis fallido";
  if (flow.status === "done") return "Análisis completo";
  return flow.stages.find((stage) => stage.state === "running")?.label ?? "Analizando";
}

export function elapsedSeconds(flow: FlowJob): number {
  return Math.max(0, Math.round((Date.parse(flow.updated_at) - Date.parse(flow.created_at)) / 1000));
}
