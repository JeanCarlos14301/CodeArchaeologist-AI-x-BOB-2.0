import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, jobsApi, setEngine as setApiEngine } from "./api";
import { ModeBadge } from "./components/ui";
import { EXAMPLE_DOSSIER, EXAMPLE_JOB } from "./fixtures";
import { adaptDossier, auditJobToFlow, jobStatusToFlow } from "./lib/jobsAdapter";
import { simulateJob } from "./lib/simulate";
import { useTheme } from "./lib/theme";
import type { BobStatus, Dossier, EngineId, FlowJob, JobStatusRaw, SampleInfo } from "./types";
import { ArchitectureView } from "./views/ArchitectureView";
import { DownloadsView } from "./views/DownloadsView";
import { FindingsView } from "./views/FindingsView";
import { HomeView, type StartRequest } from "./views/HomeView";
import { MigrationView } from "./views/MigrationView";
import { NeuralView } from "./views/NeuralView";
import { SummaryView } from "./views/SummaryView";

const POLL_INTERVAL_MS = 1000;
const FIXTURE_JOB_ID = EXAMPLE_JOB.id;

type ViewId = "home" | "neural" | "summary" | "findings" | "architecture" | "migration" | "downloads";

const NAV: { id: ViewId; label: string; icon: string }[] = [
  { id: "home", label: "Inicio", icon: "⌂" },
  { id: "neural", label: "Mapa neuronal", icon: "✦" },
  { id: "summary", label: "Resumen", icon: "▤" },
  { id: "findings", label: "Hallazgos", icon: "⚑" },
  { id: "architecture", label: "Arquitectura", icon: "◇" },
  { id: "migration", label: "Migración", icon: "⇄" },
  { id: "downloads", label: "Descargas", icon: "⇩" },
];

const isActive = (job: FlowJob | null | undefined) => job?.status === "queued" || job?.status === "running";
const finished = (raw: JobStatusRaw) => raw.status === "completed" || raw.status === "completed_with_warnings";
const pipelineMs = (raw: JobStatusRaw) => raw.events.filter((event) => event.status === "completed").reduce((sum, event) => sum + event.duration_ms, 0);

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [view, setView] = useState<ViewId>("home");
  const [bob, setBob] = useState<BobStatus | null>(null);
  const [bobError, setBobError] = useState<string | null>(null);
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [engine, setEngineState] = useState<EngineId | null>(null);
  const [offline, setOffline] = useState(false);
  const [jobs, setJobs] = useState<FlowJob[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [flow, setFlow] = useState<FlowJob | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const cancelSimulation = useRef<(() => void) | null>(null);

  const fail = useCallback((err: Error) => {
    if (err instanceof ApiError && err.status === 0) setOffline(true);
    else setError(err.message);
  }, []);

  const refreshJobs = useCallback(
    (which: EngineId | null) => {
      if (which === "jobs") jobsApi.list().then((list) => setJobs(list.map(jobStatusToFlow))).catch(fail);
      else if (which === "audits") api.audits().then((list) => setJobs(list.map(auditJobToFlow))).catch(fail);
    },
    [fail],
  );

  // Arranque: detectar qué motor expone el backend (el despliegue público apaga /api/jobs).
  useEffect(() => {
    api.bobStatus().then(setBob).catch((err: Error) => {
      setBobError(err.message);
      fail(err);
    });
    jobsApi
      .available()
      .then((ok) => {
        const chosen: EngineId = ok ? "jobs" : "audits";
        setApiEngine(chosen);
        setEngineState(chosen);
        refreshJobs(chosen);
        if (!ok) api.samples().then(setSamples).catch(fail);
      })
      .catch(fail);
  }, [fail, refreshJobs]);

  // Sondeo del análisis seleccionado hasta que termine.
  useEffect(() => {
    if (!selectedId || selectedId === FIXTURE_JOB_ID || !engine) return;
    let cancelled = false;
    let timer: number | undefined;
    const next = () => {
      timer = window.setTimeout(load, POLL_INTERVAL_MS);
    };

    const load = () => {
      if (engine === "jobs") {
        jobsApi
          .status(selectedId)
          .then(async (raw) => {
            if (cancelled) return;
            setFlow(jobStatusToFlow(raw));
            if (finished(raw)) {
              const result = await jobsApi.result(selectedId);
              if (cancelled) return;
              setDossier(adaptDossier(result, pipelineMs(raw)));
              refreshJobs("jobs");
            } else if (raw.status === "failed" || raw.status === "cancelled") refreshJobs("jobs");
            else next();
          })
          .catch((err: Error) => !cancelled && fail(err));
      } else {
        api
          .audit(selectedId)
          .then((data) => {
            if (cancelled) return;
            setFlow(auditJobToFlow(data.job));
            setDossier(data.dossier);
            if (data.job.status === "queued" || data.job.status === "running") next();
            else refreshJobs("audits");
          })
          .catch((err: Error) => !cancelled && fail(err));
      }
    };
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [selectedId, engine, refreshJobs, fail]);

  useEffect(() => () => cancelSimulation.current?.(), []);

  const reset = () => {
    cancelSimulation.current?.();
    setError(null);
    setFocusId(null);
    setFlow(null);
    setDossier(null);
  };

  const startFixture = (label: string) => {
    reset();
    setSelectedId(FIXTURE_JOB_ID);
    cancelSimulation.current = simulateJob(
      label,
      (job) => setFlow(auditJobToFlow(job)),
      () => setDossier({ ...EXAMPLE_DOSSIER, repo_name: label.replace(/\.zip$/i, "") || EXAMPLE_DOSSIER.repo_name }),
    );
  };

  const start = ({ source, mode, file, liveToken }: StartRequest) => {
    if (offline || !engine) return startFixture(source === "zip" && file ? file.name : "facturaya-v1");
    reset();
    if (engine === "jobs") {
      jobsApi
        .start(source, mode, file)
        .then(({ job_id }) => {
          setSelectedId(job_id);
          refreshJobs("jobs");
        })
        .catch(fail);
      return;
    }
    const sample = source === "holdout" ? samples.find((item) => /holdout/i.test(item.id)) : samples.find((item) => !/holdout/i.test(item.id));
    if (source === "zip" || !sample) return startFixture(source === "zip" && file ? file.name : source);
    api
      .startAudit(sample.id, mode, liveToken ?? "")
      .then((job) => {
        setSelectedId(job.id);
        refreshJobs("audits");
      })
      .catch(fail);
  };

  const selectJob = (id: string) => {
    reset();
    setSelectedId(id);
  };

  const resultsJobId = flow && flow.status === "done" ? flow.id : null;
  const busy = isActive(flow) || jobs.some((item) => isActive(item));

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
            {offline && <span className="rounded-md bg-warn/10 px-2 py-0.5 text-[11px] font-semibold text-warn ring-1 ring-inset ring-warn/30">DEMO OFFLINE</span>}
            {!offline && engine && <span className="hidden rounded-md bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-muted sm:inline">{engine === "jobs" ? "/api/jobs · 11 etapas" : "/api/audits"}</span>}
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
            <HomeView engine={engine} offline={offline} bob={bob} bobError={bobError} busy={busy} job={flow} jobs={jobs} error={error} onStart={start} onSelectJob={selectJob} onOpenResults={() => go("summary")} />
          )}
          {view === "neural" && <NeuralView flow={flow} onGoHome={() => go("home")} onOpenFinding={openFinding} />}
          {view === "summary" && <SummaryView dossier={dossier} onGoHome={() => go("home")} onOpenFindings={() => go("findings")} onOpenFinding={openFinding} />}
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
