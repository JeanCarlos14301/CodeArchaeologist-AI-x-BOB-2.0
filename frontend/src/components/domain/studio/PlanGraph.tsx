import { useMemo, useState } from "react";
import { Eyebrow } from "../../ui/Layout";
import type { MigrationPlan, PlanStep } from "../../../types";

const RISK = { low: { glyph: "○", label: "Riesgo bajo", tone: "text-risk-low" }, medium: { glyph: "●", label: "Riesgo medio", tone: "text-risk-medium" }, high: { glyph: "▲", label: "Riesgo alto", tone: "text-risk-high" } } as const;
const LEVEL = { low: "baja", medium: "media", high: "alta" } as const;
const KIND: Record<string, string> = {
  runtime: "Entorno", dependencies: "Dependencias", code: "Código", config: "Configuración", data: "Datos", tests: "Pruebas", infra: "Infraestructura", cutover: "Puesta en marcha",
};
const ACTION = { modify: { glyph: "~", label: "modifica", tone: "text-warning" }, create: { glyph: "+", label: "crea", tone: "text-verified" }, delete: { glyph: "−", label: "borra", tone: "text-danger" } } as const;

/** Nivel de cada paso: 0 sin dependencias, 1 + el mayor nivel de sus dependencias. */
function levels(plan: MigrationPlan): PlanStep[][] {
  const byId = new Map(plan.steps.map((step) => [step.id, step]));
  const memo = new Map<string, number>();
  const level = (step: PlanStep): number => {
    const known = memo.get(step.id);
    if (known !== undefined) return known;
    memo.set(step.id, 0); // protege de ciclos (el backend ya los rechaza)
    const value = step.depends_on.length ? 1 + Math.max(...step.depends_on.map((id) => level(byId.get(id) ?? step))) : 0;
    memo.set(step.id, value);
    return value;
  };
  const rows: PlanStep[][] = [];
  for (const step of plan.steps) (rows[level(step)] ??= []).push(step);
  return rows.filter(Boolean);
}

interface Props {
  plan: MigrationPlan;
  runs?: Record<string, "done" | "failed" | "skipped" | "running">;
  onOpenFile: (path: string) => void;
}

/** Plan como dependencias entre pasos, no como lista: lo que se puede hacer en paralelo comparte fila (PRODUCT.md §16). */
export function PlanGraph({ plan, runs = {}, onOpenFile }: Props) {
  const rows = useMemo(() => levels(plan), [plan]);
  const [selectedId, setSelectedId] = useState(plan.steps[0]?.id ?? null);
  const selected = plan.steps.find((step) => step.id === selectedId) ?? plan.steps[0];
  const number = (id: string) => plan.steps.findIndex((step) => step.id === id) + 1;

  return (
    <div>
      <div className="grid gap-x-10 gap-y-3 @3xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <p className="text-body text-pretty text-fg">{plan.summary}</p>
        <div><Eyebrow>Si algo falla</Eyebrow><p className="mt-1 text-caption text-pretty text-muted">{plan.rollback}</p></div>
      </div>

      <div className="mt-6 grid gap-x-8 gap-y-6 @4xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <ol aria-label="Secuencia de pasos">
          {rows.map((row, rowIndex) => (
            <li key={rowIndex}>
              {rowIndex > 0 && (
                <div aria-hidden className="ml-4 flex h-6 items-center gap-2 text-decor">
                  <span className="h-full w-px bg-line-strong" />
                  {row.length > 1 && <span className="text-micro tracking-eyebrow uppercase text-subtle">pueden hacerse en paralelo</span>}
                </div>
              )}
              <ul className={`grid gap-2 ${row.length > 1 ? "@xl:grid-cols-2" : ""}`}>
                {row.map((step) => {
                  const risk = RISK[step.risk];
                  const run = runs[step.id];
                  const active = step.id === selected?.id;
                  return (
                    <li key={step.id}>
                      <button type="button" onClick={() => setSelectedId(step.id)} aria-current={active ? "true" : undefined}
                        className={`grid w-full grid-cols-[2rem_minmax(0,1fr)] gap-x-3 rounded-inner border px-3 py-2.5 text-left transition-[border-color,background-color] duration-150 ease-out ${active ? "border-accent-hover bg-raised" : "border-line hover:border-line-strong hover:bg-raised"}`}>
                        <span className={`flex h-7 w-7 items-center justify-center rounded-pill border font-mono text-micro ${run === "done" ? "border-verified/50 text-verified" : run === "failed" ? "border-danger/50 text-danger" : run === "running" ? "border-fg text-activity" : "border-line-strong text-fg-2"}`}>
                          {run === "done" ? "✓" : run === "failed" ? "✗" : run === "running" ? <span aria-hidden className="h-1.5 w-1.5 animate-pulse rounded-pill bg-activity" /> : String(number(step.id)).padStart(2, "0")}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-body text-fg">{step.title}</span>
                          <span className="mt-0.5 flex flex-wrap items-center gap-x-3 text-caption text-subtle">
                            <span>{KIND[step.kind] ?? step.kind}</span>
                            <span className={risk.tone}><span aria-hidden>{risk.glyph} </span>{risk.label}</span>
                            {step.depends_on.length > 0 && <span className="font-mono">↳ {step.depends_on.map((id) => String(number(id)).padStart(2, "0")).join(", ")}</span>}
                            {run === "skipped" && <span>omitido</span>}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ol>

        {selected && (
          <aside aria-label={`Detalle del paso ${selected.title}`} className="rounded-panel border border-line bg-surface p-5 @4xl:sticky @4xl:top-4 @4xl:self-start">
            <Eyebrow>Paso {String(number(selected.id)).padStart(2, "0")} · {KIND[selected.kind] ?? selected.kind}</Eyebrow>
            <h3 className="mt-1 font-display text-title text-fg">{selected.title}</h3>
            <p className="mt-2 text-body text-pretty text-fg-2">{selected.why}</p>
            <dl className="mt-4 space-y-4 text-caption">
              <div><dt className="text-micro tracking-eyebrow text-subtle uppercase">Qué cambia</dt><dd className="mt-1 text-body text-pretty whitespace-pre-line text-fg-2">{selected.changes}</dd></div>
              {selected.files.length > 0 && (
                <div>
                  <dt className="text-micro tracking-eyebrow text-subtle uppercase">Archivos</dt>
                  <dd className="mt-1">
                    <ul className="space-y-1 font-mono">
                      {selected.files.map((file) => {
                        const action = ACTION[file.action];
                        return (
                          <li key={`${file.action}-${file.path}`} className="grid grid-cols-[1.25rem_1fr_auto] items-baseline gap-1">
                            <span aria-hidden className={action.tone}>{action.glyph}</span>
                            {file.action === "create" ? <span className="truncate text-fg">{file.path}</span> : (
                              <button type="button" onClick={() => onOpenFile(file.path)} className="truncate text-left text-fg hover:underline">{file.path}</button>
                            )}
                            <span className="font-sans text-subtle">{action.label}</span>
                          </li>
                        );
                      })}
                    </ul>
                  </dd>
                </div>
              )}
              <div><dt className="text-micro tracking-eyebrow text-subtle uppercase">Cómo validarlo</dt><dd className="mt-1 text-body text-pretty text-fg-2">{selected.validation}</dd></div>
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-subtle">
                <span className={RISK[selected.risk].tone}><span aria-hidden>{RISK[selected.risk].glyph} </span>{RISK[selected.risk].label}</span>
                <span>Complejidad {LEVEL[selected.complexity]}</span>
              </div>
            </dl>
          </aside>
        )}
      </div>
    </div>
  );
}
