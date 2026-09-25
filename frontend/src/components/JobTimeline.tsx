import type { Job } from "../types";

const STAGES: { id: string; label: string; detail: string }[] = [
  { id: "preparing", label: "Sandbox", detail: "Copia aislada del repo, sin material de evaluación" },
  { id: "auditing", label: "evidence-auditor", detail: "Bob audita y delega en subagentes" },
  { id: "validating", label: "Validador", detail: "Python verifica archivo, líneas y fragmento" },
  { id: "done", label: "Expediente", detail: "Hallazgos con evidencia verificada" },
];

function stageIndex(job: Job): number {
  if (job.status === "done") return STAGES.length;
  const index = STAGES.findIndex((stage) => stage.id === job.stage);
  return index === -1 ? 0 : index;
}

export function JobTimeline({ job }: { job: Job }) {
  const current = stageIndex(job);
  const failed = job.status === "failed";

  return (
    <div className="space-y-2">
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {STAGES.map((stage, index) => {
          const done = index < current;
          const active = index === current && !failed && job.status !== "done";
          const tone = done
            ? "border-emerald-300 bg-emerald-50"
            : active
              ? "border-amber-300 bg-amber-50"
              : failed && index === current
                ? "border-rose-300 bg-rose-50"
                : "border-stone-200 bg-white";
          return (
            <li key={stage.id} className={`rounded-md border p-2 ${tone}`}>
              <p className="flex items-center gap-1.5 text-xs font-semibold">
                {active && <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" aria-hidden />}
                {stage.label}
              </p>
              <p className="text-[11px] leading-snug text-stone-600">{stage.detail}</p>
            </li>
          );
        })}
      </ol>
      {failed && (
        <p role="alert" className="rounded-md bg-rose-50 p-2 text-sm text-rose-800">
          {job.error ?? "La auditoría falló."}
        </p>
      )}
    </div>
  );
}
