import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { AuditLauncher } from "./components/AuditLauncher";
import { BobStatusPanel } from "./components/BobStatusPanel";
import { EvidenceViewer } from "./components/EvidenceViewer";
import { FindingsList } from "./components/FindingsList";
import { JobHistory } from "./components/JobHistory";
import { JobTimeline } from "./components/JobTimeline";
import { StatsBar } from "./components/StatsBar";
import type { AuditDetail, BobStatus, Evidence, ExecutionMode, Job, SampleInfo } from "./types";

const POLL_INTERVAL_MS = 1500;

function isActive(job: Job | undefined): boolean {
  return job?.status === "queued" || job?.status === "running";
}

export default function App() {
  const [bob, setBob] = useState<BobStatus | null>(null);
  const [bobError, setBobError] = useState<string | null>(null);
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AuditDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<{ findingId: string; evidenceIndex: number; evidence: Evidence } | null>(null);

  const refreshJobs = useCallback(() => {
    api.audits().then(setJobs).catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    api.bobStatus().then(setBob).catch((err: Error) => setBobError(err.message));
    api.samples().then(setSamples).catch((err: Error) => setError(err.message));
    refreshJobs();
  }, [refreshJobs]);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    let timer: number | undefined;
    const load = () => {
      api
        .audit(selectedId)
        .then((data) => {
          if (cancelled) return;
          setDetail(data);
          if (isActive(data.job)) {
            timer = window.setTimeout(load, POLL_INTERVAL_MS);
          } else {
            refreshJobs();
          }
        })
        .catch((err: Error) => !cancelled && setError(err.message));
    };
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [selectedId, refreshJobs]);

  const startAudit = (sample: string, mode: ExecutionMode) => {
    setError(null);
    api
      .startAudit(sample, mode)
      .then((job) => {
        setDetail(null);
        setSelection(null);
        setSelectedId(job.id);
        refreshJobs();
      })
      .catch((err: Error) => setError(err.message));
  };

  const selectJob = (id: string) => {
    setDetail(null);
    setSelection(null);
    setSelectedId(id);
  };

  const dossier = detail?.dossier ?? null;
  const running = jobs.some((job) => isActive(job));

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">CodeArchaeologist</h1>
        <p className="text-sm text-stone-600">
          Auditoría de código heredado con IBM Bob: cada hallazgo apunta a un archivo y unas líneas verificadas por código.
        </p>
      </header>

      {error && (
        <p role="alert" className="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-800">
          {error}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="space-y-6">
          <div className="rounded-lg border border-stone-200 bg-white p-4">
            <AuditLauncher samples={samples} busy={running} onStart={startAudit} />
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4">
            <BobStatusPanel status={bob} error={bobError} />
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-4">
            <h2 className="mb-2 text-sm font-semibold text-stone-800">Historial</h2>
            <JobHistory jobs={jobs} selectedId={selectedId} onSelect={selectJob} />
          </div>
        </aside>

        <main className="min-w-0 space-y-4">
          {!detail && (
            <div className="rounded-lg border border-dashed border-stone-300 p-10 text-center text-sm text-stone-500">
              Lanza una auditoría o elige una del historial.
            </div>
          )}
          {detail && <JobTimeline job={detail.job} />}
          {detail && dossier && (
            <>
              <StatsBar dossier={dossier} />
              <div className="grid gap-4 xl:grid-cols-2">
                <FindingsList
                  findings={dossier.findings}
                  rejected={dossier.rejected_findings}
                  checks={dossier.evidence_checks}
                  selected={selection}
                  onSelect={(finding, evidence, index) =>
                    setSelection({ findingId: finding.id, evidenceIndex: index, evidence })
                  }
                />
                <div className="xl:sticky xl:top-4 xl:self-start">
                  <EvidenceViewer jobId={detail.job.id} evidence={selection?.evidence ?? null} />
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
