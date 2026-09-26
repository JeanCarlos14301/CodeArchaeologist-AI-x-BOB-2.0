import type { FlowJob } from "../types";

const DOT: Record<string, string> = {
  done: "bg-ok text-bg",
  running: "border-2 border-accent text-accent",
  failed: "bg-bad text-bg",
  pending: "border border-line text-muted",
};

function formatMs(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** Línea de tiempo vertical: una fila por etapa real del pipeline, con duración y mensaje del backend. */
export function Timeline({ job, onSelectStage, selectedStage }: { job: FlowJob; onSelectStage?: (n: number) => void; selectedStage?: number | null }) {
  const doneCount = job.stages.filter((stage) => stage.state === "done").length;

  return (
    <div>
      <div className="mb-4 flex items-center gap-3" aria-label={`Progreso ${job.progress}%`}>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
          <div
            className={`h-full rounded-full transition-all duration-500 ${job.status === "failed" ? "bg-bad" : "bg-accent"}`}
            style={{ width: `${job.status === "done" ? 100 : job.progress}%` }}
          />
        </div>
        <span className="font-mono text-xs text-muted">
          {doneCount}/{job.stages.length} etapas
        </span>
      </div>

      <ol className="relative space-y-1">
        {job.stages.map((stage, index) => {
          const clickable = !!onSelectStage && stage.state !== "pending";
          const Row = clickable ? "button" : "div";
          return (
            <li key={stage.id} aria-current={stage.state === "running" ? "step" : undefined} className="relative">
              {index < job.stages.length - 1 && <span aria-hidden className={`absolute left-3.75 top-8 h-[calc(100%-8px)] w-px ${stage.state === "done" ? "bg-ok/50" : "bg-line"}`} />}
              <Row
                {...(clickable ? { type: "button" as const, onClick: () => onSelectStage(stage.number) } : {})}
                className={`flex w-full items-start gap-3 rounded-lg px-1.5 py-1.5 text-left transition ${selectedStage === stage.number ? "bg-accent/10" : clickable ? "hover:bg-surface-2" : ""}`}
              >
                <span className={`z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface text-xs font-bold ${DOT[stage.state]}`}>
                  {stage.state === "done" ? "✓" : stage.state === "failed" ? "!" : stage.state === "running" ? <span className="h-2 w-2 animate-pulse rounded-full bg-accent" /> : stage.number}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className={`text-sm font-medium ${stage.state === "pending" ? "text-muted" : ""}`}>{stage.label}</span>
                    {stage.duration_ms !== null && <span className="shrink-0 font-mono text-[11px] text-muted">{formatMs(stage.duration_ms)}</span>}
                  </span>
                  {stage.message && stage.state !== "pending" && <span className="block text-xs leading-snug text-muted">{stage.message}</span>}
                </span>
              </Row>
            </li>
          );
        })}
      </ol>

      {job.status === "failed" && (
        <p role="alert" className="mt-3 rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
          {job.error ?? "El análisis falló."}
        </p>
      )}
    </div>
  );
}
