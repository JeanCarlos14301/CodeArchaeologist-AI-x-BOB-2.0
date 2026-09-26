import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Search } from "lucide-react";
import { formatDate, jobLabel } from "../../lib/format";
import { SEVERITY, bySeverity } from "../../lib/severity";
import { collectFiles } from "../../lib/tree";
import { useResource, useWorkspace } from "../../lib/workspace";
import { Kbd } from "../ui/Badge";
import { NAV } from "./NavRail";

interface Command {
  id: string;
  group: string;
  label: string;
  hint?: string;
  prefix?: string;
  prefixTone?: string;
  run: () => void;
}

const MAX_RESULTS = 60;

export function CommandPalette() {
  const ws = useWorkspace();
  const { paletteOpen, setPaletteOpen, route, navigate, go, dossier, jobs, openShowcase, seedComposer, setAiOpen, aiOpen } = ws;
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const architecture = useResource("architecture").data;

  useEffect(() => {
    if (!paletteOpen) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    setQuery("");
    setActive(0);
    requestAnimationFrame(() => input.current?.focus());
    return () => previousFocus.current?.focus?.();
  }, [paletteOpen]);

  const commands = useMemo<Command[]>(() => {
    const close = (fn: () => void) => () => { setPaletteOpen(false); fn(); };
    const list: Command[] = [
      { id: "new", group: "Acciones", label: "Analizar un repositorio nuevo", hint: "Subir ZIP", run: close(() => navigate({ jobId: null })) },
      { id: "showcase", group: "Acciones", label: "Abrir la auditoría real de FacturaYa", hint: "Grabada · no consume bobcoins", run: close(() => void openShowcase()) },
      { id: "ai", group: "Acciones", label: aiOpen ? "Cerrar el panel de Bob" : "Abrir el panel de Bob", hint: "⌘J", run: close(() => setAiOpen(!aiOpen)) },
    ];
    if (route.jobId) {
      list.push({ id: "ask", group: "Acciones", label: "Preguntar a Bob sobre este repositorio", hint: "Gasta bobcoins", run: close(() => seedComposer("")) });
      for (const item of NAV) list.push({ id: `nav-${item.id}`, group: "Navegar", label: `Ir a ${item.label}`, hint: item.question, run: close(() => go(item.id)) });
    }
    for (const finding of [...(dossier?.findings ?? [])].sort(bySeverity)) {
      const severity = SEVERITY[finding.severity];
      list.push({
        id: `f-${finding.id}`, group: "Hallazgos", label: finding.title, hint: finding.id,
        prefix: severity.glyph, prefixTone: severity.text, run: close(() => go("risks", { finding: finding.id })),
      });
    }
    for (const file of collectFiles(architecture, dossier)) {
      list.push({ id: `file-${file.path}`, group: "Archivos", label: file.path, hint: `${file.functions} funciones · ${file.findings.length} hallazgos`, run: close(() => go("repository", { file: file.path })) });
    }
    for (const job of jobs.slice(0, 8)) {
      list.push({ id: `job-${job.id}`, group: "Análisis recientes", label: jobLabel(job.label), hint: `${job.status} · ${formatDate(job.created_at)}`, run: close(() => navigate({ jobId: job.id, section: "overview" })) });
    }
    return list;
  }, [route.jobId, dossier, architecture, jobs, aiOpen, go, navigate, openShowcase, seedComposer, setAiOpen, setPaletteOpen]);

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = needle ? commands.filter((c) => `${c.label} ${c.hint ?? ""} ${c.group}`.toLowerCase().includes(needle)) : commands;
    return filtered.slice(0, MAX_RESULTS);
  }, [commands, query]);

  useEffect(() => setActive(0), [query]);

  if (!paletteOpen) return null;

  const onKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => Math.min(results.length - 1, i + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(0, i - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      results[active]?.run();
    } else if (event.key === "Escape") {
      event.preventDefault();
      setPaletteOpen(false);
    } else if (event.key === "Tab") {
      event.preventDefault();
    }
  };

  let lastGroup = "";
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-canvas/70 px-4 pt-[12vh]" onMouseDown={() => setPaletteOpen(false)}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Paleta de comandos"
        onMouseDown={(event) => event.stopPropagation()}
        className="w-full max-w-xl animate-enter overflow-hidden rounded-panel border border-line-strong bg-overlay shadow-pop"
      >
        <div className="flex items-center gap-2.5 border-b border-line px-4">
          <Search size={16} aria-hidden className="text-subtle" />
          <input
            ref={input}
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-list"
            aria-activedescendant={results[active] ? `cmd-${results[active].id}` : undefined}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onKey}
            placeholder="Busca un hallazgo, archivo, sección o acción…"
            className="h-12 flex-1 bg-transparent text-body text-fg placeholder:text-subtle focus:outline-none"
          />
          <Kbd>Esc</Kbd>
        </div>
        <p aria-live="polite" className="sr-only">{results.length === 0 ? "Sin resultados" : `${results.length} resultados`}</p>
        <ul id="palette-list" role="listbox" aria-label="Resultados" className="max-h-[60vh] overflow-y-auto p-1.5">
          {results.length === 0 && <li className="px-3 py-6 text-center text-body text-muted">Nada coincide con “{query}”.</li>}
          {results.map((command, index) => {
            const header = command.group !== lastGroup ? command.group : null;
            lastGroup = command.group;
            return (
              <li key={command.id} role="presentation">
                {header && <p className="px-3 pt-3 pb-1 text-micro tracking-eyebrow text-subtle uppercase">{header}</p>}
                <div
                  id={`cmd-${command.id}`}
                  role="option"
                  aria-selected={index === active}
                  onMouseEnter={() => setActive(index)}
                  onClick={command.run}
                  className={`flex cursor-pointer items-center gap-3 rounded-inner px-3 py-2 ${index === active ? "bg-raised" : ""}`}
                >
                  {command.prefix && <span aria-hidden className={`text-caption ${command.prefixTone ?? "text-subtle"}`}>{command.prefix}</span>}
                  <span className="min-w-0 flex-1 truncate text-body text-fg">{command.label}</span>
                  {command.hint && <span className="shrink-0 truncate font-mono text-micro text-subtle">{command.hint}</span>}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
