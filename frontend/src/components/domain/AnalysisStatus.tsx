import { elapsedSeconds, statusLabel } from "../../lib/flow";
import type { FlowJob } from "../../types";

const MARK: Record<string, { glyph: string; tone: string }> = {
  done: { glyph: "✓", tone: "text-verified" },
  running: { glyph: "●", tone: "text-activity animate-pulse" },
  failed: { glyph: "✗", tone: "text-danger" },
  pending: { glyph: "○", tone: "text-subtle" },
};

/** Progreso por etapas reales, sin porcentajes inventados (PRODUCT.md §27). */
export function AnalysisStatus({ flow }: { flow: FlowJob }) {
  const running = flow.status === "running" || flow.status === "queued";
  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <p className="text-body font-medium text-fg" aria-live="polite">{statusLabel(flow)}</p>
        {flow.status !== "queued" && <p className="font-mono text-caption text-subtle tabular-nums">{elapsedSeconds(flow)} s</p>}
      </div>
      <div className="mb-4 h-0.5 overflow-hidden rounded-pill bg-raised">
        {running ? (
          <div className="spectrum-rail h-full w-full" />
        ) : (
          <div className={`h-full ${flow.status === "failed" ? "bg-danger" : "bg-verified"}`} style={{ width: flow.status === "done" ? "100%" : `${flow.progress}%` }} />
        )}
      </div>
      <ol className="space-y-2.5">
        {flow.stages.map((stage) => {
          const mark = MARK[stage.state];
          return (
            <li key={stage.id} aria-current={stage.state === "running" ? "step" : undefined} className="grid grid-cols-[1rem_1fr] gap-x-3">
              <span aria-hidden className={`text-caption leading-5 ${mark.tone}`}>{mark.glyph}</span>
              <div>
                <p className={`text-body leading-5 ${stage.state === "pending" ? "text-subtle" : "text-fg"}`}>{stage.label}</p>
                <p className="text-caption text-subtle">{stage.detail}</p>
              </div>
            </li>
          );
        })}
      </ol>
      {flow.status === "failed" && (
        <div role="alert" className="mt-4 rounded-inner border border-danger/40 bg-danger/5 px-4 py-3">
          <p className="text-body text-fg">El análisis no pudo completarse.</p>
          <p className="mt-1 font-mono text-caption text-fg-2">{flow.error ?? "Error sin detalle."}</p>
          <p className="mt-2 text-caption text-muted">Revisa que el ZIP sea un repositorio Python + Flask + SQLite de menos de 5 MB e inténtalo de nuevo.</p>
        </div>
      )}
    </div>
  );
}
