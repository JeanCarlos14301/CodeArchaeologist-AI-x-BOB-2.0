import { EXAMPLE_JOB } from "../fixtures";
import type { Job } from "../types";

export const STAGES = [
  { id: "preparing", label: "Sandbox", detail: "Copia aislada del repositorio, sin material de evaluación" },
  { id: "auditing", label: "Auditoría con Bob", detail: "evidence-auditor recorre el código y emite hallazgos" },
  { id: "validating", label: "Validación", detail: "Python comprueba archivo, líneas y fragmento de cada evidencia" },
  { id: "done", label: "Expediente", detail: "Hallazgos con evidencia verificada" },
] as const;

const STEP_MS = 900;

/** Recorre las etapas con fixture cuando no hay backend. Devuelve la función de cancelación. */
export function simulateJob(sample: string, onUpdate: (job: Job) => void, onDone: () => void): () => void {
  const now = new Date().toISOString();
  const base: Job = { ...EXAMPLE_JOB, sample, created_at: now, updated_at: now, status: "queued", stage: "queued" };
  const timers: number[] = [];
  onUpdate(base);
  STAGES.forEach((stage, index) => {
    timers.push(
      window.setTimeout(() => {
        const last = index === STAGES.length - 1;
        onUpdate({ ...base, status: last ? "done" : "running", stage: stage.id, updated_at: new Date().toISOString() });
        if (last) onDone();
      }, (index + 1) * STEP_MS),
    );
  });
  return () => timers.forEach((timer) => window.clearTimeout(timer));
}
