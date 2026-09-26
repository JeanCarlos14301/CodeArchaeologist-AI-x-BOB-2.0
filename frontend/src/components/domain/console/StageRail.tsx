import { formatClock, stageMetric, STAGE_ORDER, type ActivityModel } from "../../../lib/activity";
import type { StageId } from "../../../types";

export const STAGE_INFO: Record<StageId, { label: string; running: string; detail: string }> = {
  preparing: { label: "Repositorio indexado", running: "Indexando repositorio", detail: "Extracción segura en un sandbox; el código nunca se ejecuta." },
  auditing: { label: "Auditoría de IBM Bob", running: "Bob analiza el código", detail: "evidence-auditor recorre el código y delega en subagentes especializados." },
  validating: { label: "Evidencia verificada", running: "Verificando evidencia", detail: "Python comprueba archivo, líneas y fragmento de cada hallazgo." },
  migration: { label: "Primer corte probado", running: "Probando primer corte", detail: "Pruebas de caracterización contra el legado y el corte moderno." },
  done: { label: "Expediente listo", running: "Generando expediente", detail: "Solo quedan hallazgos cuya evidencia coincide con el código." },
};

export type StageState = "pending" | "running" | "done" | "failed";

const MARK: Record<StageState, { glyph: string; tone: string; label: string }> = {
  done: { glyph: "✓", tone: "text-verified border-verified/40", label: "completada" },
  running: { glyph: "●", tone: "text-activity border-activity/40 animate-pulse", label: "en curso" },
  failed: { glyph: "✗", tone: "text-danger border-danger/50", label: "falló" },
  pending: { glyph: "", tone: "text-subtle border-line", label: "pendiente" },
};

/** Estado de cada etapa según los eventos visibles (sirve igual en vivo y en reproducción). */
export function stageStates(model: ActivityModel, settled: boolean): Record<StageId, StageState> {
  const reached = STAGE_ORDER.filter((stage) => model.stages[stage].events > 0);
  const last = reached[reached.length - 1];
  const lastIndex = last ? STAGE_ORDER.indexOf(last) : -1;
  return Object.fromEntries(STAGE_ORDER.map((stage, index) => {
    let state: StageState = "pending";
    if (model.failure?.stage === stage) state = "failed";
    else if (stage === "done" && model.done) state = "done";
    else if (index < lastIndex) state = "done";
    else if (index === lastIndex) state = settled && !model.failure ? "done" : model.failure ? "pending" : "running";
    return [stage, state];
  })) as Record<StageId, StageState>;
}

interface Props {
  model: ActivityModel;
  states: Record<StageId, StageState>;
  selected: StageId;
  onSelect: (stage: StageId) => void;
  /** id del panel que muestra la etapa elegida (aria-controls). */
  panelId: string;
}

export function StageRail({ model, states, selected, onSelect, panelId }: Props) {
  return (
    <ol aria-label="Etapas del análisis" className="relative">
      {STAGE_ORDER.map((stage, index) => {
        const state = states[stage];
        const mark = MARK[state];
        const info = STAGE_INFO[stage];
        const times = model.stages[stage];
        const metric = stageMetric(model, stage);
        const active = selected === stage;
        const elapsed = times.start !== null && times.end !== null && times.end > times.start ? formatClock(times.end - times.start) : null;
        return (
          <li key={stage} className="relative">
            {index < STAGE_ORDER.length - 1 && (
              <span aria-hidden className={`absolute top-10 bottom-0 left-[1.4rem] w-px ${state === "done" ? "bg-verified/40" : "bg-line"}`} />
            )}
            <button
              type="button"
              onClick={() => onSelect(stage)}
              aria-current={active ? "step" : undefined}
              aria-controls={panelId}
              className={`relative grid w-full grid-cols-[1.75rem_1fr] gap-x-3 rounded-inner px-2 py-2.5 text-left transition-[background-color] duration-150 hover:bg-raised ${active ? "bg-raised shadow-inset-accent" : ""}`}
            >
              <span className={`z-10 flex h-7 w-7 items-center justify-center rounded-pill border bg-canvas font-mono text-caption ${mark.tone}`}>
                <span aria-hidden>{mark.glyph || index + 1}</span>
              </span>
              <span className="min-w-0">
                <span className="flex items-baseline justify-between gap-2">
                  <span className={`text-body ${state === "pending" ? "text-subtle" : "text-fg"}`}>{state === "running" ? info.running : info.label}</span>
                  {elapsed && <span className="font-mono text-micro text-subtle tabular-nums">{elapsed}</span>}
                </span>
                <span className="block truncate text-caption text-subtle">{metric ?? info.detail}</span>
                <span className="sr-only">Etapa {index + 1}, {mark.label}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
