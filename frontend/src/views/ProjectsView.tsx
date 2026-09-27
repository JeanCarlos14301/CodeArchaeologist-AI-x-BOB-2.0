import { useRef, useState, type DragEvent } from "react";
import { ArrowRight, UploadCloud } from "lucide-react";
import { AnalysisStatus } from "../components/domain/AnalysisStatus";
import { ModeBadge, StatusDot } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataList, Eyebrow, Section, Segmented } from "../components/ui/Layout";
import { ErrorState } from "../components/ui/States";
import { formatDate, jobLabel } from "../lib/format";
import { isActive } from "../lib/flow";
import { useWorkspace } from "../lib/workspace";

const MAX_ZIP_MB = 5; // backend/app/pipeline/ingestion.py: MAX_ZIP_COMPRESSED_BYTES
// "showcase" opens the recorded FacturaYa audit; GitHub and local folders are not offered until they work.
type Source = "zip" | "showcase";
type Purpose = "audit" | "modernization";

export function ProjectsView() {
  const { jobs, bob, offline, notice, dismissNotice, startUpload, openShowcase, navigate, tokenRequired } = useWorkspace();
  const [source, setSource] = useState<Source>("showcase");
  const [purpose, setPurpose] = useState<Purpose>("audit");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [token, setTokenDraft] = useState("");
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const picker = useRef<HTMLInputElement>(null);

  const active = jobs.find((job) => isActive(job)) ?? null;
  const bobReady = bob ? bob.installed && bob.api_key_configured : false;
  const modernizeOnly = purpose === "modernization";
  const canStart = !offline && (modernizeOnly || (bobReady && !active)) && !!file && (!tokenRequired || token.trim().length > 0) && !submitting;
  const blockedBy = offline ? "The backend is not responding." : !bob ? "Checking IBM Bob…" : !bobReady ? "IBM Bob is not ready on the server." : active ? "An analysis is already running." : null;

  const pick = (candidate: File | undefined) => {
    setFileError(null);
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".zip")) return setFileError("The file must be a .zip of the repository.");
    if (candidate.size > MAX_ZIP_MB * 1024 * 1024) return setFileError(`The ZIP weighs ${(candidate.size / 1024 / 1024).toFixed(1)} MB; the maximum is ${MAX_ZIP_MB} MB.`);
    setFile(candidate);
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files[0]);
  };

  const start = async () => {
    if (!file || !canStart) return;
    setSubmitting(true);
    await startUpload(file, token.trim(), purpose);
    setSubmitting(false);
  };

  return (
    <div className="px-6 pt-10 pb-12 @3xl:px-10">
      <header className="max-w-3xl">
        <Eyebrow>CodeArchaeologist × IBM Bob</Eyebrow>
        <h1 className="mt-3 font-display text-display font-normal text-balance text-fg">
          Understand a legacy system{" "}
          <span className="relative inline-block">
            before you touch it.
            <span aria-hidden className="absolute -bottom-1 left-0 h-0.5 w-full rounded-pill bg-spectrum" />
          </span>
        </h1>
        <p className="mt-4 max-w-2xl text-body text-pretty text-muted">
          Connect a repository. IBM Bob audits it and every finding is checked against the code —file, lines and snippet—
          before it reaches your architecture, your risks and your migration plan.
        </p>
      </header>

      {notice && (
        <div className="mt-6 max-w-3xl">
          <ErrorState title="The action did not complete." message={notice} onRetry={dismissNotice} retryLabel="Dismiss" />
        </div>
      )}

      <div className="mt-10 grid grid-cols-1 gap-x-12 gap-y-4 @5xl:grid-cols-[minmax(0,1fr)_minmax(300px,380px)]">
        <div>
          <Section eyebrow="01 · Connect" title="Repository to analyze" className="pt-0">
            <Segmented<Source>
              label="Repository source"
              value={source}
              onChange={setSource}
              options={[
                { value: "zip", label: "Upload ZIP" },
                { value: "showcase", label: "FacturaYa · already generated", hint: "A real IBM Bob audit, recorded; spends no bobcoins" },
              ]}
            />

            {source === "zip" ? (
              <div className="mt-5 space-y-4">
                <div>
                  <span className="mb-1.5 block text-caption text-muted">What do you want to do</span>
                  <Segmented<Purpose>
                    label="What to do with the repository"
                    value={purpose}
                    onChange={setPurpose}
                    options={[
                      { value: "audit", label: "Audit with evidence" },
                      { value: "modernization", label: "Modernization only", hint: "Any language or framework; it does not audit or spend bobcoins on upload" },
                    ]}
                  />
                  <p className="mt-2 text-caption text-pretty text-subtle">
                    {modernizeOnly
                      ? "Any language, framework, monolith or microservices. It measures your stack and lets you choose where to migrate; Bob only works when you ask."
                      : "Findings verified against the code, architecture, risks and a migration plan."}
                  </p>
                </div>
                <div
                  onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  className={`flex flex-col items-center rounded-composer border border-dashed px-6 py-9 text-center transition-[border-color,background-color] duration-150 ${dragging ? "border-accent-hover bg-raised" : "border-line-strong bg-surface"}`}
                >
                  <input ref={picker} type="file" accept=".zip,application/zip" className="sr-only" aria-label="Select the repository ZIP" onChange={(event) => pick(event.target.files?.[0])} />
                  <UploadCloud size={22} aria-hidden className="text-subtle" />
                  {file ? (
                    <p className="mt-3 font-mono text-body text-fg">{file.name} <span className="text-subtle">· {(file.size / 1024).toFixed(0)} KB</span></p>
                  ) : (
                    <p className="mt-3 text-body text-fg-2">Drop the repository .zip here</p>
                  )}
                  <Button size="sm" variant="ghost" className="mt-2" onClick={() => picker.current?.click()}>
                    {file ? "Choose another file" : "Choose file"}
                  </Button>
                  {fileError && <p role="alert" className="mt-2 text-caption text-danger">{fileError}</p>}
                </div>

                <div className={`grid grid-cols-1 gap-3 ${tokenRequired ? "@xl:grid-cols-[minmax(0,1fr)_auto] @xl:items-end" : ""}`}>
                  {tokenRequired && (
                    <label className="block min-w-0">
                      <span className="mb-1.5 block text-caption text-muted">Access token (required: each analysis spends bobcoins)</span>
                      <input type="password" autoComplete="off" value={token} onChange={(event) => setTokenDraft(event.target.value)}
                        className="h-9 w-full rounded-pill border border-line bg-control px-4 font-mono text-caption text-fg focus:border-focus focus:outline-none" />
                    </label>
                  )}
                  <Button variant="primary" className={tokenRequired ? "" : "w-fit"} disabled={!canStart} onClick={() => void start()} icon={<ArrowRight size={14} aria-hidden />}>
                    {submitting ? "Sending the repository…" : modernizeOnly ? "Open in the Modernization Studio" : "Start the repository analysis"}
                  </Button>
                </div>
                <p className="text-caption text-subtle">
                  Up to {MAX_ZIP_MB} MB · the code is analyzed statically and never runs.{!tokenRequired && !modernizeOnly && " Each analysis spends bobcoins from the server's IBM Bob account."}
                  {blockedBy && !modernizeOnly && <span className="text-warning"> {blockedBy}</span>}
                </p>
              </div>
            ) : (
              <div className="mt-5 rounded-panel border border-line-strong bg-surface px-5 py-6">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-mono text-body text-fg">facturaya-v1</p>
                  <ModeBadge mode="imported" />
                </div>
                <p className="mt-2 max-w-xl text-body text-pretty text-muted">
                  An already generated analysis of a legacy invoicing system: a real IBM Bob reply, recorded, with evidence
                  verified against the code and a tested first migration cut. Opening it spends no bobcoins and needs no token.
                </p>
                <Button variant="primary" className="mt-4" disabled={offline} onClick={() => void openShowcase()} icon={<ArrowRight size={14} aria-hidden />}>
                  Open the FacturaYa analysis
                </Button>
              </div>
            )}
          </Section>

          {active && (
            <Section eyebrow="Running" title={jobLabel(active.label)} aside={<ModeBadge mode={active.execution_mode} />}>
              <div className="max-w-xl"><AnalysisStatus flow={active} /></div>
              <Button size="sm" variant="secondary" className="mt-4" onClick={() => navigate({ jobId: active.id, section: "session" })}>View the live session</Button>
            </Section>
          )}
        </div>

        <aside className="space-y-0">
          <Section eyebrow="History" title="Recent analyses" className="pt-0">
            {jobs.length === 0 ? (
              <p className="text-body text-muted">There are no analyses on this server yet.</p>
            ) : (
              <ul className="divide-y divide-line-subtle">
                {jobs.slice(0, 8).map((job) => (
                  <li key={job.id}>
                    <button type="button" onClick={() => navigate({ jobId: job.id, section: "overview" })} className="grid w-full grid-cols-[1fr_auto] items-center gap-x-3 gap-y-0.5 py-2.5 text-left hover:bg-raised">
                      <span className="truncate font-mono text-caption text-fg">{jobLabel(job.label)}</span>
                      <ModeBadge mode={job.execution_mode} />
                      <span className="text-caption text-subtle">{formatDate(job.created_at)}</span>
                      <span className="text-caption text-subtle">
                        <StatusDot tone={job.status === "done" ? "ok" : job.status === "failed" ? "bad" : "busy"} label={job.status === "done" ? "complete" : job.status === "failed" ? "failed" : "running"} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section eyebrow="Server" title="IBM Bob">
            {!bob ? (
              <p className="text-body text-muted">{offline ? "No connection to the backend." : "Checking…"}</p>
            ) : (
              <DataList rows={[
                { label: "Bob Shell", value: bob.installed ? <StatusDot tone="ok" label={bob.version ?? "installed"} /> : <StatusDot tone="bad" label="not installed" /> },
                { label: "API key", value: bob.api_key_configured ? <StatusDot tone="ok" label="configured" /> : <StatusDot tone="bad" label="missing" /> },
                { label: "Access", value: bob.live_requires_token ? "token required" : "open" },
                { label: "Modes · subagents · skills", value: `${bob.custom_modes.length} · ${bob.subagents.length} · ${bob.skills.length}` },
                { label: "Cap per analysis", value: `${bob.max_cost_per_run} bc · ${Math.round(bob.timeout_s / 60)} min` },
              ]} />
            )}
          </Section>
        </aside>
      </div>
    </div>
  );
}
