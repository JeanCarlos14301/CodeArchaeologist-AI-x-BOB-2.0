import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "./api";
import { ModeBadge } from "./components/ui";
import { jobToFlow } from "./lib/flow";
import { useTheme } from "./lib/theme";
import type { BobStatus, Dossier, FlowJob } from "./types";
import { ArchitectureView } from "./views/ArchitectureView";
import { DownloadsView } from "./views/DownloadsView";
import { FindingsView } from "./views/FindingsView";
import { HomeView, type StartRequest } from "./views/HomeView";
import { NeuralView } from "./views/NeuralView";
import { SummaryView } from "./views/SummaryView";

const POLL_INTERVAL_MS = 1500;

type ViewId = "home" | "neural" | "summary" | "findings" | "architecture" | "downloads";

const NAV: { id: ViewId; label: string; icon: string }[] = [
  { id: "home", label: "Inicio", icon: "⌂" },
  { id: "neural", label: "Mapa neuronal", icon: "✦" },
  { id: "summary", label: "Resumen", icon: "▤" },
  { id: "findings", label: "Hallazgos", icon: "⚑" },
  { id: "architecture", label: "Arquitectura", icon: "◇" },
  { id: "downloads", label: "Descargas", icon: "⇩" },
];

const isActive = (job: FlowJob | null | undefined) => job?.status === "queued" || job?.status === "running";

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [view, setView] = useState<ViewId>("home");
  const [bob, setBob] = useState<BobStatus | null>(null);
  const [bobError, setBobError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [jobs, setJobs] = useState<FlowJob[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [flow, setFlow] = useState<FlowJob | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);

  const fail = useCallback((err: Error) => {
    if (err instanceof ApiError && err.status === 0) setOffline(true);
    else setError(err.message);
  }, []);

  const refreshJobs = useCallback(() => {
    api.audits().then((list) => setJobs(list.map(jobToFlow))).catch(fail);
  }, [fail]);

  useEffect(() => {
    api.bobStatus().then(setBob).catch((err: Error) => {
      setBobError(err.message);
      fail(err);
    });
    refreshJobs();
  }, [fail, refreshJobs]);

  // Sondeo del análisis seleccionado hasta que termine.
  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    let timer: number | undefined;
    const load = () => {
      api
        .audit(selectedId)
        .then((data) => {
          if (cancelled) return;
          setOffline(false);
          setFlow(jobToFlow(data.job));
          setDossier(data.dossier);
          if (data.job.status === "queued" || data.job.status === "running") timer = window.setTimeout(load, POLL_INTERVAL_MS);
          else refreshJobs();
        })
        .catch((err: Error) => !cancelled && fail(err));
    };
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [selectedId, refreshJobs, fail]);

  const reset = () => {
    setError(null);
    setFocusId(null);
    setFlow(null);
    setDossier(null);
  };

  const start = ({ file, token }: StartRequest) => {
    reset();
    api
      .upload(file, token)
      .then((job) => {
        setSelectedId(job.id);
        setFlow(jobToFlow(job));
        refreshJobs();
      })
      .catch(fail);
  };

  const selectJob = (id: string) => {
    reset();
    setSelectedId(id);
  };

  const resultsJobId = flow && flow.status === "done" ? flow.id : null;
  const busy = isActive(flow) || jobs.some(isActive);

  const go = (next: ViewId) => {
    setView(next);
    window.scrollTo({ top: 0 });
  };

  const openFinding = (id: string) => {
    setFocusId(id);
    go("findings");
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-375 items-center gap-3 px-4">
          <button type="button" onClick={() => go("home")} className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent font-mono text-sm text-accent-fg" aria-hidden>CA</span>
            <span className="hidden sm:inline">CodeArchaeologist</span>
          </button>
          <div className="ml-2 flex items-center gap-2">
            {(dossier || flow) && <ModeBadge mode={dossier?.execution_mode ?? flow!.execution_mode} />}
            {offline && <span className="rounded-md bg-bad/10 px-2 py-0.5 text-[11px] font-semibold text-bad ring-1 ring-inset ring-bad/30">SIN BACKEND</span>}
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
            title={theme === "dark" ? "Tema claro" : "Tema oscuro"}
            className="ml-auto flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-surface text-base hover:border-accent/50"
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </header>

      <div className="mx-auto flex max-w-375 flex-col gap-4 px-4 py-6 lg:flex-row lg:gap-8">
        <nav aria-label="Secciones" className="lg:sticky lg:top-20 lg:w-52 lg:shrink-0 lg:self-start">
          <ul className="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
            {NAV.map((item) => (
              <li key={item.id} className="shrink-0">
                <button
                  type="button"
                  onClick={() => go(item.id)}
                  aria-current={view === item.id ? "page" : undefined}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${view === item.id ? "bg-accent/10 font-medium text-accent" : "text-muted hover:bg-surface-2 hover:text-fg"}`}
                >
                  <span className="w-4 text-center" aria-hidden>{item.icon}</span>
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <main className="min-w-0 flex-1">
          {view === "home" && (
            <HomeView offline={offline} bob={bob} bobError={bobError} busy={busy} job={flow} jobs={jobs} error={error} onStart={start} onSelectJob={selectJob} onOpenResults={() => go("summary")} />
          )}
          {view === "neural" && <NeuralView flow={flow} onGoHome={() => go("home")} onOpenFinding={openFinding} />}
          {view === "summary" && <SummaryView dossier={dossier} onGoHome={() => go("home")} onOpenFindings={() => go("findings")} onOpenFinding={openFinding} />}
          {view === "findings" && <FindingsView jobId={selectedId ?? ""} dossier={dossier} focusId={focusId} onGoHome={() => go("home")} />}
          {view === "architecture" && <ArchitectureView jobId={resultsJobId} theme={theme} onGoHome={() => go("home")} />}
          {view === "downloads" && <DownloadsView jobId={resultsJobId} onGoHome={() => go("home")} />}
        </main>
      </div>
    </div>
  );
}
