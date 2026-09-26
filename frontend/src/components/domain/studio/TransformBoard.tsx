import { useEffect, useRef, useState } from "react";
import { ArrowRight, X } from "lucide-react";
import { Button } from "../../ui/Button";
import { Eyebrow, Segmented } from "../../ui/Layout";
import { cleanVersion } from "../../../lib/format";
import { TechIcon } from "./TechIcon";
import type { DetectedTech, Priority, StackReport, StackTarget } from "../../../types";

export interface Draft {
  mode: "chosen" | "recommend";
  /** tecnología actual -> destino elegido */
  mappings: Record<string, string>;
  business_context: string;
  priorities: Priority[];
}

export const EMPTY_DRAFT: Draft = { mode: "chosen", mappings: {}, business_context: "", priorities: [] };

const MIGRATABLE = ["backend", "frontend", "database", "orm", "testing", "build"];
const KIND_LABEL: Record<string, string> = {
  backend: "Backend", frontend: "Frontend", database: "Datos", orm: "Acceso a datos", testing: "Pruebas", build: "Construcción",
};
const PRIORITIES: { id: Priority; label: string }[] = [
  { id: "security", label: "Seguridad" },
  { id: "performance", label: "Rendimiento" },
  { id: "cost", label: "Costo" },
  { id: "time", label: "Tiempo de entrega" },
  { id: "team", label: "Curva del equipo" },
  { id: "compatibility", label: "Compatibilidad" },
];
const MAX_CONTEXT = 1500;
const MAX_PRIORITIES = 4;

interface Props {
  stack: StackReport;
  draft: Draft;
  onChange: (draft: Draft) => void;
  onSubmit: () => void;
  busy: boolean;
  needsToken: boolean;
  token: string;
  onToken: (token: string) => void;
  resetsWork: boolean;
}

/** Flecha entre la tecnología actual y su destino: hairline con punta, blanca cuando hay destino elegido. */
function Connector({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 56 12" aria-hidden className={`hidden h-3 w-14 shrink-0 @xl:block ${active ? "text-fg" : "text-decor"}`}>
      <line x1="0" y1="6" x2="50" y2="6" stroke="currentColor" strokeWidth="1" strokeDasharray={active ? undefined : "3 3"} />
      <path d="M46 2 L54 6 L46 10" fill="none" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

export function TransformBoard({ stack, draft, onChange, onSubmit, busy, needsToken, token, onToken, resetsWork }: Props) {
  const [open, setOpen] = useState<string | null>(null);
  const migratable = stack.technologies.filter((tech) => MIGRATABLE.includes(tech.kind));
  // Una fila por tecnología (si aparece en varios servicios, se decide una vez para todo el proyecto).
  const rows = [...new Map(migratable.map((tech) => [tech.id, tech])).values()].filter((tech) => (stack.targets[tech.id] ?? []).length > 0);
  const chosen = Object.entries(draft.mappings).filter(([from, to]) => from && to);
  const ready = draft.mode === "recommend" || chosen.length > 0;
  const picker = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(null);
    window.addEventListener("keydown", onKey);
    picker.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const set = (patch: Partial<Draft>) => onChange({ ...draft, ...patch });
  const choose = (from: string, to: string | null) => {
    const mappings = { ...draft.mappings };
    if (to) mappings[from] = to;
    else delete mappings[from];
    set({ mappings });
    setOpen(null);
  };
  const togglePriority = (id: Priority) => {
    const on = draft.priorities.includes(id);
    if (!on && draft.priorities.length >= MAX_PRIORITIES) return;
    set({ priorities: on ? draft.priorities.filter((p) => p !== id) : [...draft.priorities, id] });
  };
  const targetOf = (tech: DetectedTech): StackTarget | undefined => (stack.targets[tech.id] ?? []).find((t) => t.id === draft.mappings[tech.id]);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Segmented<Draft["mode"]>
          label="Quién elige los destinos"
          value={draft.mode}
          onChange={(mode) => set({ mode })}
          options={[{ value: "chosen", label: "Elijo yo los destinos" }, { value: "recommend", label: "Que Bob los recomiende" }]}
        />
        <p className="text-caption text-subtle">
          {draft.mode === "chosen" ? "Pulsa el destino de cada tecnología que quieras cambiar." : "Bob propondrá destinos del catálogo según tu proyecto y tu negocio."}
        </p>
      </div>

      <div className="mt-5 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-x-4 border-b border-line-subtle pb-2 text-micro text-subtle tracking-eyebrow uppercase">
        <span>Actual</span><span className="hidden w-14 @xl:block" aria-hidden /><span>Objetivo</span>
      </div>

      {rows.length === 0 ? (
        <p className="py-6 text-body text-muted">No se detectó ninguna tecnología con destinos posibles en el catálogo. Si el proyecto usa otras, Bob puede evaluarlas en modo recomendación.</p>
      ) : (
        <ul>
          {rows.map((tech) => {
            const target = targetOf(tech);
            const expanded = open === tech.id;
            const options = stack.targets[tech.id] ?? [];
            const same = options.filter((option) => option.language !== null && option.language === tech.language);
            const other = options.filter((option) => !same.includes(option));
            const evidence = tech.evidence.find((item) => item.path);
            return (
              <li key={tech.id} className="border-b border-line-subtle py-3">
                <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-x-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="text-fg"><TechIcon slug={tech.icon} name={tech.name} size={24} /></span>
                    <div className="min-w-0">
                      <p className="truncate text-body text-fg">{tech.name} {tech.version && <span className="font-mono text-caption text-subtle">{cleanVersion(tech.version)}</span>}</p>
                      <p className="truncate font-mono text-caption text-subtle">
                        <span className="font-sans uppercase tracking-eyebrow text-micro">{KIND_LABEL[tech.kind]}</span>
                        {evidence && <> · {evidence.path}{evidence.line ? `:${evidence.line}` : ""}</>}
                      </p>
                    </div>
                  </div>
                  <Connector active={!!target || draft.mode === "recommend"} />
                  <div className="flex min-w-0 items-center gap-2">
                    {draft.mode === "recommend" ? (
                      <span className="text-caption text-subtle">Bob propondrá un destino si conviene.</span>
                    ) : target ? (
                      <>
                        <button type="button" onClick={() => setOpen(expanded ? null : tech.id)} aria-expanded={expanded} aria-controls={`picker-${tech.id}`}
                          className="inline-flex h-9 min-w-0 items-center gap-2.5 rounded-pill border border-line-strong bg-raised pr-4 pl-3 text-body text-fg transition-[border-color] duration-150 ease-out hover:border-fg/40">
                          <TechIcon slug={target.icon} name={target.name} size={18} />
                          <span className="truncate">{target.name}</span>
                        </button>
                        <button type="button" aria-label={`Quitar el destino de ${tech.name}`} onClick={() => choose(tech.id, null)}
                          className="inline-flex h-7 w-7 items-center justify-center rounded-pill text-subtle hover:bg-raised hover:text-fg"><X size={14} aria-hidden /></button>
                      </>
                    ) : (
                      <button type="button" onClick={() => setOpen(expanded ? null : tech.id)} aria-expanded={expanded} aria-controls={`picker-${tech.id}`}
                        className="inline-flex h-9 items-center gap-2 rounded-pill border border-dashed border-line-strong px-4 text-caption text-muted transition-[border-color,color] duration-150 ease-out hover:border-fg/40 hover:text-fg">
                        Elegir destino <ArrowRight size={13} aria-hidden />
                      </button>
                    )}
                  </div>
                </div>

                {expanded && draft.mode === "chosen" && (
                  <div id={`picker-${tech.id}`} ref={picker} role="group" aria-label={`Destinos posibles para ${tech.name}`} className="mt-3 rounded-panel border border-line bg-surface p-4">
                    {[{ title: "Mismo lenguaje", items: same }, { title: same.length ? "Otro lenguaje o ecosistema" : "Destinos posibles", items: other }].map((group) => group.items.length > 0 && (
                      <div key={group.title} className="mb-3 last:mb-0">
                        <Eyebrow>{group.title}</Eyebrow>
                        <ul className="mt-2 grid grid-cols-2 gap-2 @lg:grid-cols-3 @3xl:grid-cols-4">
                          {group.items.map((option) => {
                            const selected = draft.mappings[tech.id] === option.id;
                            return (
                              <li key={option.id}>
                                <button type="button" aria-pressed={selected} onClick={() => choose(tech.id, option.id)}
                                  className={`flex h-11 w-full items-center gap-2.5 rounded-inner border px-3 text-left text-caption transition-[border-color,background-color] duration-150 ease-out ${selected ? "border-accent-hover bg-raised text-fg" : "border-line text-fg-2 hover:border-line-strong hover:bg-raised hover:text-fg"}`}>
                                  <TechIcon slug={option.icon} name={option.name} size={18} />
                                  <span className="truncate">{option.name}</span>
                                  {selected && <span aria-hidden className="ml-auto text-verified">✓</span>}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <div className="mt-6 grid gap-x-10 gap-y-5 @3xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <label className="block">
          <Eyebrow>Contexto de tu negocio</Eyebrow>
          <span className="mt-1 mb-1.5 block text-caption text-muted">Qué hace el sistema, quién lo usa y qué no puede fallar. Con esto Bob pesa seguridad frente a velocidad para TU caso.</span>
          <textarea
            value={draft.business_context}
            maxLength={MAX_CONTEXT}
            rows={4}
            onChange={(event) => set({ business_context: event.target.value })}
            placeholder="Ej.: facturación electrónica para pymes; no puede perder datos ni exponer facturas de otro cliente; picos a fin de mes."
            className="w-full resize-y rounded-inner border border-line bg-control px-3 py-2 text-body text-fg placeholder:text-subtle focus:border-focus focus:outline-none"
          />
          <span className="mt-1 block text-right font-mono text-micro text-subtle">{draft.business_context.length}/{MAX_CONTEXT}</span>
        </label>
        <fieldset>
          <legend><Eyebrow>Qué priorizas (hasta {MAX_PRIORITIES})</Eyebrow></legend>
          <ul className="mt-2 flex flex-wrap gap-2">
            {PRIORITIES.map((priority) => {
              const on = draft.priorities.includes(priority.id);
              const locked = !on && draft.priorities.length >= MAX_PRIORITIES;
              return (
                <li key={priority.id}>
                  <button type="button" aria-pressed={on} disabled={locked} onClick={() => togglePriority(priority.id)}
                    className={`inline-flex h-7 items-center gap-1.5 rounded-pill border px-3 text-caption transition-[border-color,background-color] duration-150 ease-out disabled:opacity-40 ${on ? "border-line-strong bg-raised text-fg" : "border-line text-muted hover:border-line-strong hover:text-fg"}`}>
                    {on && <span aria-hidden className="text-verified">✓</span>}{priority.label}
                  </button>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-caption text-pretty text-subtle">Toda migración cambia un equilibrio: ganar velocidad puede costar seguridad y al revés. Bob te lo explica antes de tocar nada.</p>
        </fieldset>
      </div>

      <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          {chosen.length > 0 && draft.mode === "chosen" && (
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-caption text-fg-2">
              {chosen.map(([from, to], index) => (
                <span key={from} className="inline-flex items-center gap-1.5">
                  {index > 0 && <span aria-hidden className="text-decor">·</span>}
                  {stack.technologies.find((t) => t.id === from)?.name ?? from}<span aria-hidden className="text-subtle">→</span>{(stack.targets[from] ?? []).find((t) => t.id === to)?.name ?? to}
                </span>
              ))}
            </p>
          )}
          {needsToken && (
            <label className="mt-2 block">
              <span className="mb-1 block text-caption text-muted">Token de acceso (Bob consume bobcoins)</span>
              <input type="password" autoComplete="off" value={token} onChange={(event) => onToken(event.target.value)}
                className="h-9 w-72 max-w-full rounded-pill border border-line bg-control px-4 font-mono text-caption text-fg focus:border-focus focus:outline-none" />
            </label>
          )}
          {resetsWork && <p className="mt-2 text-caption text-warning">Evaluar de nuevo descarta la evaluación, el plan y la implementación actuales.</p>}
        </div>
        <Button variant="primary" disabled={!ready || busy || !token.trim()} onClick={onSubmit} icon={<ArrowRight size={14} aria-hidden />}>
          {busy ? "Bob está evaluando…" : "Evaluar impacto con Bob"}
        </Button>
      </div>
    </div>
  );
}
