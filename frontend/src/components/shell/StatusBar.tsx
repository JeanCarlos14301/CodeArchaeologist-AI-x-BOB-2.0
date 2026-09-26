import { isActive, statusLabel } from "../../lib/flow";
import { useWorkspace } from "../../lib/workspace";
import { StatusDot } from "../ui/Badge";

/** Contexto y operaciones en segundo plano (PRODUCT.md §7): etapa, backend, Bob, trazabilidad. */
export function StatusBar() {
  const { flow, dossier, offline, bob, jobs } = useWorkspace();
  const running = jobs.find((job) => isActive(job)) ?? (flow && isActive(flow) ? flow : null);

  return (
    <footer className="relative flex h-7 min-w-0 shrink-0 items-center gap-4 overflow-hidden border-t border-line bg-canvas px-3 font-mono text-micro whitespace-nowrap text-subtle">
      {running && <span aria-hidden className="spectrum-rail absolute inset-x-0 top-0 h-px" />}
      <span className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden" aria-live="polite">
        {running ? (
          <StatusDot tone="busy" label={`${statusLabel(running)} · ${running.label}`} />
        ) : flow ? (
          <StatusDot tone={flow.status === "failed" ? "bad" : "ok"} label={statusLabel(flow)} />
        ) : (
          <StatusDot tone="idle" label="Sin análisis en curso" />
        )}
      </span>
      {dossier?.source_sha256 && <span className="hidden shrink-0 lg:inline" title={dossier.source_sha256}>sha256 {dossier.source_sha256.slice(0, 12)}</span>}
      <span className="ml-auto flex shrink-0 items-center gap-4">
        <StatusDot tone={offline ? "bad" : "ok"} label={offline ? "Backend sin conexión" : "Backend conectado"} />
        <span className="hidden sm:inline">
          {bob ? <StatusDot tone={bob.installed && bob.api_key_configured ? "ok" : "warn"} label={bob.installed ? `IBM Bob ${bob.version ?? ""}` : "Bob no instalado"} /> : "Bob …"}
        </span>
      </span>
    </footer>
  );
}
