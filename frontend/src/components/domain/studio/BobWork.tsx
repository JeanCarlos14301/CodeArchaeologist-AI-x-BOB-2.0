import { useEffect, useRef, useState } from "react";
import { Eyebrow } from "../../ui/Layout";
import type { StudioState } from "../../../types";

type StudioEvent = StudioState["events"][number];

const GLYPH: Record<string, { glyph: string; tone: string }> = {
  "bob.tool": { glyph: "›", tone: "text-fg-2" },
  "bob.edit": { glyph: "✎", tone: "text-verified" },
  "bob.skill": { glyph: "◆", tone: "text-fg-2" },
  "bob.plan": { glyph: "☰", tone: "text-fg-2" },
  "bob.thinking": { glyph: "…", tone: "text-subtle" },
  "bob.answer": { glyph: "✓", tone: "text-verified" },
  "bob.writing": { glyph: "…", tone: "text-subtle" },
  "bob.result": { glyph: "✓", tone: "text-verified" },
  "bob.tool.error": { glyph: "✗", tone: "text-danger" },
  "bob.subagent.start": { glyph: "⇢", tone: "text-activity" },
  "bob.subagent.end": { glyph: "⇠", tone: "text-fg-2" },
  "bob.subagent.report": { glyph: "⇠", tone: "text-fg-2" },
  validator: { glyph: "▲", tone: "text-warning" },
  info: { glyph: "·", tone: "text-subtle" },
};
const MAX_VISIBLE = 14;

function useElapsed(since: number | null): number {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return since === null ? 0 : Math.max(0, Math.round(now - since));
}

const isRead = (event: StudioEvent) => event.kind === "bob.tool" && ["read_file", "list_files"].includes(String(event.data.tool));
const isSearch = (event: StudioEvent) => event.kind === "bob.tool" && ["search_files", "grep", "codebase_search", "glob"].includes(String(event.data.tool));

interface Props {
  /** Título de lo que hace Bob ahora (arriba, con el cronómetro). */
  title: string;
  events: StudioEvent[];
  /** Instante (s) en que empezó la fase; por defecto, el del primer evento. */
  since?: number | null;
}

/**
 * Lo que Bob está haciendo de verdad: cada línea sale del stream real de Bob o del validador del backend
 * (lecturas, búsquedas, subagentes, ediciones, rechazos). Nada de progreso inventado ni porcentajes.
 */
export function BobWork({ title, events, since }: Props) {
  const start = since ?? events[0]?.t ?? null;
  const elapsed = useElapsed(start);
  const visible = events.slice(-MAX_VISIBLE);
  const end = useRef<HTMLLIElement>(null);
  const counters = [
    { label: "lecturas", value: events.filter(isRead).length },
    { label: "búsquedas", value: events.filter(isSearch).length },
    { label: "ediciones", value: events.filter((event) => event.kind === "bob.edit").length },
    { label: "subagentes", value: events.filter((event) => event.kind === "bob.subagent.start").length },
  ].filter((counter) => counter.value > 0);

  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest" });
  }, [events.length]);

  return (
    <div role="status" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <p className="flex items-center gap-2 text-body text-fg"><span aria-hidden className="h-1.5 w-1.5 animate-pulse rounded-pill bg-activity" />{title}</p>
        <p className="flex flex-wrap items-center gap-x-4 font-mono text-caption text-subtle tabular-nums">
          <span>{elapsed} s</span>
          {counters.map((counter) => <span key={counter.label}>{counter.value} {counter.label}</span>)}
        </p>
      </div>
      <div className="mt-3">
        <Eyebrow>Actividad de Bob, en directo</Eyebrow>
        <ul className="mt-2 max-h-72 space-y-1 overflow-y-auto border-l border-line pl-4">
          {visible.length === 0 && <li className="text-caption text-subtle">Esperando el primer movimiento de Bob… (arrancar la sesión puede tardar unos segundos)</li>}
          {visible.map((event, index) => {
            const style = GLYPH[event.kind] ?? GLYPH.info;
            return (
              <li key={`${event.t}-${index}`} ref={index === visible.length - 1 ? end : undefined} className="grid grid-cols-[1.25rem_minmax(0,1fr)] text-caption">
                <span aria-hidden className={style.tone}>{style.glyph}</span>
                <span className="min-w-0">
                  <span className={`${event.kind === "bob.thinking" ? "text-muted" : "text-fg-2"}`}>{event.message}</span>
                  {event.actor && event.kind.startsWith("bob.subagent") && <span className="ml-2 font-mono text-micro text-subtle">{event.actor}</span>}
                  {event.detail && <span className="block truncate text-subtle" title={event.detail}>{event.detail}</span>}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
