import { isActive, statusLabel } from "../../lib/flow";
import { useWorkspace } from "../../lib/workspace";
import { visibleSteps } from "../domain/AskBob";
import { StatusDot } from "../ui/Badge";

/** Context and background operations (PRODUCT.md §7): stage, backend, Bob, traceability. */
export function StatusBar() {
  const { flow, dossier, offline, bob, jobs, askHistory } = useWorkspace();
  const running = jobs.find((job) => isActive(job)) ?? (flow && isActive(flow) ? flow : null);
  // Bob working on a chat question: visible from any screen, with its real steps.
  const asking = askHistory.find((entry) => entry.status === "pending");
  const steps = asking ? visibleSteps(asking.progress) : [];
  const askLabel = asking
    ? `Bob is answering your question${steps.length ? ` · ${steps.length} ${steps.length === 1 ? "step" : "steps"} · ${steps[steps.length - 1].message}` : ""}`
    : null;

  return (
    <footer className="relative flex h-7 min-w-0 shrink-0 items-center gap-4 overflow-hidden border-t border-line bg-canvas px-3 font-mono text-micro whitespace-nowrap text-subtle">
      {running && <span aria-hidden className="spectrum-rail absolute inset-x-0 top-0 h-px" />}
      <span className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden" aria-live="polite">
        {running ? (
          <StatusDot tone="busy" label={`${statusLabel(running)} · ${running.label}`} />
        ) : flow ? (
          <StatusDot tone={flow.status === "failed" ? "bad" : "ok"} label={statusLabel(flow)} />
        ) : (
          <StatusDot tone="idle" label="No analysis running" />
        )}
      </span>
      {askLabel && <span className="hidden min-w-0 max-w-2/5 shrink truncate sm:inline"><StatusDot tone="busy" label={askLabel} /></span>}
      {dossier?.source_sha256 && !askLabel && <span className="hidden shrink-0 lg:inline" title={dossier.source_sha256}>sha256 {dossier.source_sha256.slice(0, 12)}</span>}
      <span className="ml-auto flex shrink-0 items-center gap-4">
        <StatusDot tone={offline ? "bad" : "ok"} label={offline ? "Backend offline" : "Backend connected"} />
        <span className="hidden sm:inline">
          {bob ? <StatusDot tone={bob.installed && bob.api_key_configured ? "ok" : "warn"} label={bob.installed ? `IBM Bob ${bob.version ?? ""}` : "Bob not installed"} /> : "Bob …"}
        </span>
      </span>
    </footer>
  );
}
