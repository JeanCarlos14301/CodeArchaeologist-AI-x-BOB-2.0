import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api } from "./api";
import { ModeBadge } from "./components/ui";
import { EXAMPLE_DOSSIER, EXAMPLE_JOB } from "./fixtures";
import { simulateJob } from "./lib/simulate";
import { useTheme } from "./lib/theme";
import type { AuditDetail, BobStatus, ExecutionMode, Job, SampleInfo } from "./types";
import { ArchitectureView } from "./views/ArchitectureView";
import { DownloadsView } from "./views/DownloadsView";
import { FindingsView } from "./views/FindingsView";
import { HomeView } from "./views/HomeView";
import { MigrationView } from "./views/MigrationView";
import { SummaryView } from "./views/SummaryView";

const POLL_INTERVAL_MS = 1500;
const FIXTURE_JOB_ID = EXAMPLE_JOB.id;

type ViewId = "home" | "summary" | "findings" | "architecture" | "migration" | "downloads";

const NAV: { id: ViewId; label: string; icon: string }[] = [
  { id: "home", label: "Inicio", icon: "⌂" },
  { id: "summary", label: "Resumen", icon: "▤" },
  { id: "findings", label: "Hallazgos", icon: "⚑" },
  { id: "architecture", label: "Arquitectura", icon: "◇" },
  { id: "migration", label: "Migración", icon: "⇄" },
  { id: "downloads", label: "Descargas", icon: "⇩" },
];

function isActive(job: Job | null | undefined): boolean {
  return job?.status === "queued" || job?.status === "running";
}

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [view, setView] = useState<ViewId>("home");
  const [bob, setBob] = useState<BobStatus | null>(null);
  const [bobError, setBobError] = useState<string | null>(null);
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [offline, setOffline] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AuditDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const cancelSimulation = useRef<(() => void) | null>(null);

  const fail = useCallback((err: Error) => {
    if (err instanceof ApiError && err.status === 0) setOffline(true);
    else setError(err.message);
  }, []);

  const refreshJobs = useCallback(() => {
    api.audits().then(setJobs).catch(fail);
  }, [fail]);

  useEffect(() => {
    api.bobStatus().then(setBob).catch((err: Error) => {
      setBobError(err.message);
      fail(err);
    });
    api.samples().then(setSamples).catch(fail);
    refreshJobs();
  }, [fail, refreshJobs]);

  // Sondeo del job real hasta que termine.
  useEffect(() => {
    if (!selectedId || selectedId === FIXTURE_JOB_ID) return;
    let cancelled = false;
    let timer: number | undefined;
    const load = () => {
      api
        .audit(selectedId)
        .then((data) => {
          if (cancelled) return;
          setDetail(data);
          if (isActive(data.job)) timer = window.setTimeout(load, POLL_INTERVAL_MS);
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

  useEffect(() => () => cancelSimulation.current?.(), []);

  const reset = () => {
    cancelSimulation.current?.();
    setError(null);
    setFocusId(null);
    setDetail(null);
  };

  const startSample = (sample: string, mode: ExecutionMode, liveToken: string) => {
    reset();
    api
      .startAudit(sample, mode, liveToken)
      .then((job) => {
        setSelectedId(job.id);
        refreshJobs();
      })
      .catch(fail);
  };

  const startFixture = (label: string) => {
    reset();
    setSelectedId(FIXTURE_JOB_ID);
    cancelSimulation.current = simulateJob(
      label,
      (job) => setDetail({ job, dossier: null }),
      () => setDetail((current) => (current ? { ...current, dossier: { ...EXAMPLE_DOSSIER, repo_name: label.replace(/\.zip$/i, "") || EXAMPLE_DOSSIER.repo_name } } : current)),
    );
  };

  const selectJob = (id: string) => {
    reset();
    setSelectedId(id);
  };

  const job = detail?.job ?? null;
  const dossier = detail?.dossier ?? null;
  const resultsJobId = job && job.status === "done" ? job.id : null;
  const busy = isActive(job) || jobs.some((item) => isActive(item));

  const go = (next: ViewId) => {
    setView(next);
    window.scrollTo({ top: 0 });
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
            {dossier && <ModeBadge mode={dossier.execution_mode} />}
            {offline && <span className="rounded-md bg-warn/10 px-2 py-0.5 text-[11px] font-semibold text-warn ring-1 ring-inset ring-warn/30">DEMO OFFLINE</span>}
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
            <HomeView
              samples={samples}
              offline={offline}
              bob={bob}
              bobError={bobError}
              busy={busy}
              job={job}
              jobs={jobs}
              error={error}
              onStartSample={startSample}
              onStartFixture={startFixture}
              onSelectJob={selectJob}
              onOpenResults={() => go("summary")}
            />
          )}
          {view === "summary" && (
            <SummaryView
              dossier={dossier}
              onGoHome={() => go("home")}
              onOpenFindings={() => go("findings")}
              onOpenFinding={(id) => {
                setFocusId(id);
                go("findings");
              }}
            />
          )}
          {view === "findings" && (
            <FindingsView jobId={selectedId ?? ""} dossier={dossier} canFetchSource={!offline && selectedId !== FIXTURE_JOB_ID} focusId={focusId} onGoHome={() => go("home")} />
          )}
          {view === "architecture" && <ArchitectureView jobId={resultsJobId} theme={theme} onGoHome={() => go("home")} />}
          {view === "migration" && <MigrationView jobId={resultsJobId} />}
          {view === "downloads" && <DownloadsView jobId={resultsJobId} />}
        </main>
      </div>
    </div>
  );
}
