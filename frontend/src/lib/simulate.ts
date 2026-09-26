import { EXAMPLE_JOB } from "../fixtures";
import type { Job } from "../types";

const STAGES = [{ id: "preparing" }, { id: "auditing" }, { id: "validating" }, { id: "done" }] as const;

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
