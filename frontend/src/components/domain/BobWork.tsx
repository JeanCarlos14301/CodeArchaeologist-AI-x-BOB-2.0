import { useEffect, useRef, useState } from "react";
import { Eyebrow } from "../ui/Layout";

/** Un paso real de Bob: del stream de Bob o del validador del backend (Estudio o chat). */
export interface BobWorkEvent {
  t: number;
  kind: string;
  message: string;
  actor?: string | null;
  detail?: string | null;
  data: Record<string, string | number | null>;
}

export const BOB_GLYPH: Record<string, { glyph: string; tone: string }> = {
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
const MAX_VISIBLE_COMPACT = 8;
const PINNED_SLACK_PX = 24;
const ANNOUNCE_EVERY_MS = 5000;

function useElapsed(since: number | null): number {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return since === null ? 0 : Math.max(0, Math.round(now - since));
}

/** Resumen para lectores de pantalla como mucho cada pocos segundos: nunca un anuncio por acción de Bob. */
function useThrottled(text: string): string {
  const [announced, setAnnounced] = useState(text);
  const last = useRef(0);
  useEffect(() => {
    const wait = Math.max(0, last.current + ANNOUNCE_EVERY_MS - Date.now());
    const timer = window.setTimeout(() => {
      last.current = Date.now();
      setAnnounced(text);
    }, wait);
    return () => window.clearTimeout(timer);
  }, [text]);
  return announced;
}

const isRead = (event: BobWorkEvent) => event.kind === "bob.tool" && ["read_file", "list_files"].includes(String(event.data.tool));
const isSearch = (event: BobWorkEvent) => event.kind === "bob.tool" && ["search_files", "grep", "codebase_search", "glob"].includes(String(event.data.tool));

const plural = (value: number, one: string, many: string) => (value === 1 ? one : many);

/** Contadores de lo que Bob hizo (medidos sobre sus eventos reales), con la etiqueta en singular o plural. */
export function bobCounters(events: BobWorkEvent[]): { label: string; value: number }[] {
  const reads = events.filter(isRead).length;
  const searches = events.filter(isSearch).length;
  const edits = events.filter((event) => event.kind === "bob.edit").length;
  const agents = events.filter((event) => event.kind === "bob.subagent.start").length;
  return [
    { label: plural(reads, "lectura", "lecturas"), value: reads },
    { label: plural(searches, "búsqueda", "búsquedas"), value: searches },
    { label: plural(edits, "edición", "ediciones"), value: edits },
    { label: plural(agents, "subagente", "subagentes"), value: agents },
  ].filter((counter) => counter.value > 0);
}

interface Props {
  /** Título de lo que hace Bob ahora (arriba, con el cronómetro). */
  title: string;
  events: BobWorkEvent[];
  /** Instante (s epoch) en que empezó; por defecto, el del primer evento. */
  since?: number | null;
  /** Variante estrecha para el panel de Bob. */
  compact?: boolean;
}

/**
 * Lo que Bob está haciendo de verdad: cada línea sale del stream real de Bob o del validador del backend
 * (lecturas, búsquedas, subagentes, ediciones, rechazos). Nada de progreso inventado ni porcentajes.
 */
export function BobWork({ title, events, since, compact = false }: Props) {
  const start = since ?? events[0]?.t ?? null;
  const elapsed = useElapsed(start);
  const limit = compact ? MAX_VISIBLE_COMPACT : MAX_VISIBLE;
  const visible = events.slice(-limit);
  const offset = events.length - visible.length;
  const list = useRef<HTMLUListElement>(null);
  const pinned = useRef(true);
  const counters = bobCounters(events);
  const last = events[events.length - 1];
  const announcement = useThrottled(`${title}. ${counters.map((c) => `${c.value} ${c.label}`).join(", ")}${last ? `. Último paso: ${last.message}` : ""}`);

  // Solo se desplaza la propia lista, y solo si estaba al final: la página nunca salta mientras lees.
  useEffect(() => {
    const el = list.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  const onScroll = () => {
    const el = list.current;
    if (el) pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < PINNED_SLACK_PX;
  };

  return (
    <div className="relative">
      <p role="status" className="sr-only">{announcement}</p>
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
        <p className={`flex items-center gap-2 text-fg ${compact ? "text-caption" : "text-body"}`}>
          <span aria-hidden className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-pill bg-activity" />{title}
        </p>
        <p className="flex flex-wrap items-center gap-x-3 font-mono text-caption text-subtle tabular-nums">
          <span>{elapsed} s</span>
          {counters.map((counter) => <span key={counter.label}>{counter.value} {counter.label}</span>)}
        </p>
      </div>
      <div className={compact ? "mt-2" : "mt-3"}>
        {!compact && <Eyebrow>Actividad de Bob, en directo</Eyebrow>}
        <ul ref={list} onScroll={onScroll} aria-label="Pasos de Bob"
          className={`${compact ? "max-h-44" : "mt-2 max-h-72"} relative space-y-1 overflow-y-auto overscroll-contain border-l border-line pl-3`}>
          {visible.length === 0 && (
            <li className="text-caption text-subtle">Esperando el primer movimiento de Bob… (arrancar la sesión puede tardar unos segundos)</li>
          )}
          {visible.map((event, index) => {
            const style = BOB_GLYPH[event.kind] ?? BOB_GLYPH.info;
            return (
              <li key={offset + index} className="grid grid-cols-[1.25rem_minmax(0,1fr)] text-caption">
                <span aria-hidden className={style.tone}>{style.glyph}</span>
                <span className="min-w-0">
                  <span className={event.kind === "bob.thinking" ? "text-muted" : "text-fg-2"}>{event.message}</span>
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
