import { useEffect, useRef, useState } from "react";
import { ArrowRight, X } from "lucide-react";
import { Button } from "../../ui/Button";
import { Eyebrow, Segmented } from "../../ui/Layout";
import { cleanVersion } from "../../../lib/format";
import { TechIcon } from "./TechIcon";
import type { DetectedTech, Priority, StackReport, StackTarget } from "../../../types";

export interface Draft {
  mode: "chosen" | "recommend";
  /** current technology -> chosen target */
  mappings: Record<string, string>;
  business_context: string;
  priorities: Priority[];
}

export const EMPTY_DRAFT: Draft = { mode: "chosen", mappings: {}, business_context: "", priorities: [] };

const MIGRATABLE = ["backend", "frontend", "database", "orm", "testing", "build"];
const KIND_LABEL: Record<string, string> = {
  backend: "Backend", frontend: "Frontend", database: "Data", orm: "Data access", testing: "Testing", build: "Build",
};
const PRIORITIES: { id: Priority; label: string }[] = [
  { id: "security", label: "Security" },
  { id: "performance", label: "Performance" },
  { id: "cost", label: "Cost" },
  { id: "time", label: "Time to delivery" },
  { id: "team", label: "Team learning curve" },
  { id: "compatibility", label: "Compatibility" },
];
const MAX_CONTEXT = 1500;
const MAX_PRIORITIES = 4;

interface Props {
  stack: StackReport;
  draft: Draft;
  onChange: (draft: Draft) => void;
  onSubmit: () => void;
  busy: boolean;
  /** The server requires the access token (locked mode): show its field and require it. */
  needsToken: boolean;
  token: string;
  onToken: (token: string) => void;
  resetsWork: boolean;
}

/** Arrow between the current technology and its target: a hairline with a tip, white when a target is chosen. */
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
  // One row per technology (if it shows up in several services, it is decided once for the whole project).
  const rows = [...new Map(migratable.map((tech) => [tech.id, tech])).values()].filter((tech) => (stack.targets[tech.id] ?? []).length > 0);
  const chosen = Object.entries(draft.mappings).filter(([from, to]) => from && to);
  const ready = draft.mode === "recommend" || chosen.length > 0;
  const picker = useRef<HTMLDivElement>(null);
  // Trigger of each row ("Choose target" or the chosen target): it gets the focus back when the picker closes.
  const triggers = useRef<Record<string, HTMLButtonElement | null>>({});
  const focusTrigger = (id: string) => requestAnimationFrame(() => triggers.current[id]?.focus());

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(null);
      focusTrigger(open);
    };
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
    focusTrigger(from);
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
          label="Who chooses the targets"
          value={draft.mode}
          onChange={(mode) => set({ mode })}
          options={[{ value: "chosen", label: "I choose the targets" }, { value: "recommend", label: "Let Bob recommend them" }]}
        />
        <p className="text-caption text-subtle">
          {draft.mode === "chosen" ? "Click the target for each technology you want to change." : "Bob will propose targets from the catalog based on your project and your business."}
        </p>
      </div>

      <div className="mt-5 hidden items-center gap-x-4 border-b border-line-subtle pb-2 text-micro text-subtle tracking-eyebrow uppercase @md:grid @md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <span>Current</span><span className="hidden w-14 @xl:block" aria-hidden /><span>Target</span>
      </div>

      {rows.length === 0 ? (
        <p className="py-6 text-body text-muted">No technology with possible targets in the catalog was detected. If the project uses others, Bob can assess them in recommendation mode.</p>
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
                <div className="grid grid-cols-1 items-center gap-x-4 gap-y-2 @md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
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
                      <span className="text-caption text-subtle">Bob will propose a target if it pays off.</span>
                    ) : target ? (
                      <>
                        <button type="button" ref={(el) => { triggers.current[tech.id] = el; }} onClick={() => setOpen(expanded ? null : tech.id)} aria-expanded={expanded} aria-controls={`picker-${tech.id}`}
                          aria-label={`Target for ${tech.name}: ${target.name}. Change`}
                          className="inline-flex h-9 min-w-0 items-center gap-2.5 rounded-pill border border-line-strong bg-raised pr-4 pl-3 text-body text-fg transition-[border-color] duration-150 ease-out hover:border-fg/40">
                          <TechIcon slug={target.icon} name={target.name} size={18} />
                          <span className="truncate">{target.name}</span>
                        </button>
                        <button type="button" aria-label={`Remove the target for ${tech.name}`} onClick={() => choose(tech.id, null)}
                          className="inline-flex h-7 w-7 items-center justify-center rounded-pill text-subtle hover:bg-raised hover:text-fg"><X size={14} aria-hidden /></button>
                      </>
                    ) : (
                      <button type="button" ref={(el) => { triggers.current[tech.id] = el; }} onClick={() => setOpen(expanded ? null : tech.id)} aria-expanded={expanded} aria-controls={`picker-${tech.id}`}
                        aria-label={`Choose a target for ${tech.name}`}
                        className="inline-flex h-9 items-center gap-2 rounded-pill border border-dashed border-line-strong px-4 text-caption text-muted transition-[border-color,color] duration-150 ease-out hover:border-fg/40 hover:text-fg">
                        Choose target <ArrowRight size={13} aria-hidden />
                      </button>
                    )}
                  </div>
                </div>

                {expanded && draft.mode === "chosen" && (
                  <div id={`picker-${tech.id}`} ref={picker} role="group" aria-label={`Possible targets for ${tech.name}`} className="mt-3 rounded-panel border border-line bg-surface p-4">
                    {[{ title: "Same language", items: same }, { title: same.length ? "Another language or ecosystem" : "Possible targets", items: other }].map((group) => group.items.length > 0 && (
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

      <div className="mt-6 grid grid-cols-1 gap-x-10 gap-y-5 @3xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <label className="block">
          <Eyebrow>Your business context</Eyebrow>
          <span className="mt-1 mb-1.5 block text-caption text-muted">What the system does, who uses it and what cannot fail. With this, Bob weighs security against speed for YOUR case.</span>
          <textarea
            value={draft.business_context}
            maxLength={MAX_CONTEXT}
            rows={4}
            onChange={(event) => set({ business_context: event.target.value })}
            placeholder="E.g.: e-invoicing for small businesses; it cannot lose data or expose another customer's invoices; peaks at month end."
            className="w-full resize-y rounded-inner border border-line bg-control px-3 py-2 text-body text-fg placeholder:text-subtle focus:border-focus focus:outline-none"
          />
          <span className="mt-1 block text-right font-mono text-micro text-subtle">{draft.business_context.length}/{MAX_CONTEXT}</span>
        </label>
        <fieldset>
          <legend><Eyebrow>What you prioritize (up to {MAX_PRIORITIES})</Eyebrow></legend>
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
          <p className="mt-3 text-caption text-pretty text-subtle">Every migration shifts a balance: gaining speed can cost security and vice versa. Bob explains it to you before touching anything.</p>
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
              <span className="mb-1 block text-caption text-muted">Access token (Bob spends bobcoins)</span>
              <input type="password" autoComplete="off" value={token} onChange={(event) => onToken(event.target.value)}
                className="h-9 w-72 max-w-full rounded-pill border border-line bg-control px-4 font-mono text-caption text-fg focus:border-focus focus:outline-none" />
            </label>
          )}
          {resetsWork && <p className="mt-2 text-caption text-warning">Assessing again discards the current assessment, plan and implementation.</p>}
        </div>
        {/* Primary only before the first assessment: afterwards the main action is the next phase. */}
        <Button variant={resetsWork ? "secondary" : "primary"} disabled={!ready || busy || (needsToken && !token.trim())} onClick={onSubmit} icon={<ArrowRight size={14} aria-hidden />}>
          {busy ? "Bob is assessing…" : resetsWork ? "Assess again with Bob" : "Assess the impact with Bob"}
        </Button>
      </div>
    </div>
  );
}
