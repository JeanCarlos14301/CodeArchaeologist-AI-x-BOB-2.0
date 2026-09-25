import { STAGES } from "../lib/simulate";
import type { Job } from "../types";

function currentIndex(job: Job): number {
  if (job.status === "done") return STAGES.length;
  const index = STAGES.findIndex((stage) => stage.id === job.stage);
  return index === -1 ? 0 : index;
}

export function Timeline({ job }: { job: Job }) {
  const current = currentIndex(job);
  const failed = job.status === "failed";

  return (
    <div>
      <ol className="grid gap-3 sm:grid-cols-4">
        {STAGES.map((stage, index) => {
          const done = index < current;
          const active = index === current && !failed && job.status !== "done";
          const broken = failed && index === current;
          const dot = done ? "bg-ok text-bg" : active ? "border-2 border-accent text-accent" : broken ? "bg-bad text-bg" : "border border-line text-muted";
          return (
            <li key={stage.id} aria-current={active ? "step" : undefined} className={`rounded-lg border p-3 transition ${active ? "border-accent/60 bg-accent/5" : broken ? "border-bad/50 bg-bad/5" : "border-line bg-surface"}`}>
              <div className="flex items-center gap-2">
                <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${dot}`}>
                  {done ? "✓" : broken ? "!" : active ? <span className="h-2 w-2 animate-pulse rounded-full bg-accent" /> : index + 1}
                </span>
                <span className="text-sm font-semibold">{stage.label}</span>
              </div>
              <p className="mt-2 text-xs leading-snug text-muted">{stage.detail}</p>
            </li>
          );
        })}
      </ol>
      {failed && (
        <p role="alert" className="mt-3 rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
          {job.error ?? "La auditoría falló."}
        </p>
      )}
    </div>
  );
}
