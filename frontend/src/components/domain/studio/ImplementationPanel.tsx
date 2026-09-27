import { useState } from "react";
import { Download, Hammer } from "lucide-react";
import { Button } from "../../ui/Button";
import { Eyebrow } from "../../ui/Layout";
import { BobWork } from "../BobWork";
import { CodeViewer, toLines } from "../CodeViewer";
import type { Implementation, MigrationPlan, StudioState } from "../../../types";

interface Props {
  plan: MigrationPlan;
  state: StudioState;
  busy: boolean;
  onImplement: () => void;
  onDownload: (name: "modernized.zip" | "migration.diff") => Promise<void>;
  loadDiff: () => Promise<string>;
}

const STATUS = {
  done: { glyph: "✓", label: "done", tone: "text-verified" },
  failed: { glyph: "✗", label: "failed", tone: "text-danger" },
  skipped: { glyph: "○", label: "skipped", tone: "text-subtle" },
} as const;

export function ImplementationPanel({ plan, state, busy, onImplement, onDownload, loadDiff }: Props) {
  const [understood, setUnderstood] = useState(false);
  const running = state.phase === "implementing";
  const result = state.implementation;
  const started = running || result !== null;

  return (
    <div>
      {!started && (
        <div className="grid grid-cols-1 gap-x-10 gap-y-5 @3xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div>
            <p className="text-body text-pretty text-fg">
              Bob will run the {plan.steps.length} steps in order on a <strong className="font-medium">copy</strong> of the project and give you back a ZIP with the result and the full diff.
            </p>
            <ul className="mt-3 space-y-1.5 text-caption text-muted">
              <li className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-verified">✓</span><span>Your original project is not modified.</span></li>
              <li className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-verified">✓</span><span>Bob runs no commands and does not run the project's code.</span></li>
              <li className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-warning">▲</span><span>The result is a draft: only its syntax is checked, it is not tested. Review it before using it.</span></li>
            </ul>
          </div>
          <div className="flex flex-col justify-end gap-4">
            <label className="flex cursor-pointer items-start gap-3 text-body text-fg-2">
              <input type="checkbox" checked={understood} onChange={(event) => setUnderstood(event.target.checked)} className="mt-1 h-4 w-4 accent-accent" />
              <span>I understand that Bob will write new code and that I must review and test it myself.</span>
            </label>
            <div><Button variant="primary" disabled={!understood || busy} onClick={onImplement} icon={<Hammer size={14} aria-hidden />}>Implement the plan with Bob</Button></div>
          </div>
        </div>
      )}

      {started && <Progress plan={plan} state={state} running={running} />}

      {result && !running && <Result result={result} onDownload={onDownload} loadDiff={loadDiff} onRetry={onImplement} busy={busy} />}
    </div>
  );
}

function Progress({ plan, state, running }: { plan: MigrationPlan; state: StudioState; running: boolean }) {
  const runs = new Map((state.implementation?.steps ?? []).map((step) => [step.step_id, step]));
  const events = state.events.filter((event) => event.phase === "implementing");
  const currentId = running ? events.filter((event) => event.step_id).slice(-1)[0]?.step_id ?? null : null;
  return (
    <div className="grid grid-cols-1 gap-x-10 gap-y-5 @3xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]" aria-live="polite">
      <div>
        <Eyebrow>Steps</Eyebrow>
        <ol className="mt-2 divide-y divide-line-subtle border-y border-line-subtle">
          {plan.steps.map((step, index) => {
            const run = runs.get(step.id);
            const live = running && step.id === currentId && !run;
            return (
              <li key={step.id} className="grid grid-cols-[1.75rem_minmax(0,1fr)_auto] items-baseline gap-2 py-2 text-caption">
                <span className={`font-mono ${run ? STATUS[run.status].tone : live ? "text-activity" : "text-subtle"}`}>
                  {run ? STATUS[run.status].glyph : live ? <span aria-hidden className="inline-block h-1.5 w-1.5 animate-pulse rounded-pill bg-activity" /> : String(index + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 text-body text-fg-2"><span className="block truncate">{step.title}</span>
                  {run?.note && <span className="block truncate text-caption text-subtle" title={run.note}>{run.note}</span>}
                  {run?.fixed.map((fix) => <span key={fix} className="block text-caption text-verified"><span aria-hidden>✓ </span>Fixed: {fix}</span>)}
                </span>
                <span className="font-mono text-subtle tabular-nums">{run ? `${run.changed.length} files` : live ? "in progress" : ""}</span>
              </li>
            );
          })}
        </ol>
      </div>
      <div>
        {running ? (
          <BobWork title={currentId ? `Bob runs step ${currentId}` : "Bob prepares the working copy"} events={events} />
        ) : (
          <>
            <Eyebrow>Activity</Eyebrow>
            <ul className="mt-2 space-y-1.5 text-caption text-muted">
              {events.slice(-8).map((event, index) => <li key={`${event.t}-${index}`} className="grid grid-cols-[1rem_1fr]"><span aria-hidden className="text-subtle">·</span><span>{event.message}</span></li>)}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

function Result({ result, onDownload, loadDiff, onRetry, busy }: { result: Implementation; onDownload: Props["onDownload"]; loadDiff: Props["loadDiff"]; onRetry: () => void; busy: boolean }) {
  const [diff, setDiff] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bad = result.checks.filter((check) => !check.ok);
  const failedStep = result.steps.some((step) => step.status === "failed");

  const download = async (name: "modernized.zip" | "migration.diff") => {
    setError(null);
    try {
      await onDownload(name);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const toggleDiff = async () => {
    if (diff !== null) return setDiff(null);
    try {
      setDiff(await loadDiff());
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="mt-6 border-t border-line pt-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>Result</Eyebrow>
          <p className="mt-1 font-mono text-body text-fg tabular-nums">
            {result.files_changed} files · <span className="text-verified">+{result.lines_added}</span> <span className="text-danger">−{result.lines_removed}</span> lines
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => void toggleDiff()}>{diff === null ? "View diff" : "Hide diff"}</Button>
          <Button variant="secondary" onClick={() => void download("migration.diff")}>Download diff</Button>
          <Button variant="primary" onClick={() => void download("modernized.zip")} icon={<Download size={14} aria-hidden />}>Download the migrated project (ZIP)</Button>
        </div>
      </div>
      {error && <p role="alert" className="mt-3 text-caption text-danger">{error}</p>}

      <ul className="mt-5 space-y-2 text-body text-fg-2">
        <li className="grid grid-cols-[1.25rem_1fr]">
          <span aria-hidden className={bad.length ? "text-danger" : "text-verified"}>{bad.length ? "✗" : "✓"}</span>
          <span>{result.checks.length === 0 ? "There were no Python, JSON, YAML or TOML files whose syntax to check." : bad.length ? `${bad.length} of ${result.checks.length} checked files have syntax errors.` : `Correct syntax in the ${result.checks.length} checkable files.`}</span>
        </li>
        {bad.map((check) => <li key={check.path} className="ml-5 font-mono text-caption text-danger">{check.path} <span className="font-sans text-subtle">· {check.detail}</span></li>)}
        {result.outside_plan.length > 0 && (
          <li className="grid grid-cols-[1.25rem_1fr]">
            <span aria-hidden className="text-warning">▲</span>
            <span>Bob touched {result.outside_plan.length} {result.outside_plan.length === 1 ? "file" : "files"} that were not in the plan: <span className="font-mono text-caption">{result.outside_plan.slice(0, 6).join(", ")}{result.outside_plan.length > 6 ? "…" : ""}</span>. Review them.</span>
          </li>
        )}
        {failedStep && (
          <li className="grid grid-cols-[1.25rem_1fr]">
            <span aria-hidden className="text-danger">✗</span>
            <span>A step failed and the following ones were skipped: the ZIP contains only what was done. <button type="button" disabled={busy} onClick={onRetry} className="text-fg underline underline-offset-2">Try again</button></span>
          </li>
        )}
        <li className="grid grid-cols-[1.25rem_1fr] text-caption text-subtle"><span aria-hidden>○</span><span>{result.not_executed}</span></li>
      </ul>

      {diff !== null && <div className="mt-5"><CodeViewer path="migration.diff" lines={toLines(diff)} maxHeight="28rem" caption={`${diff.split("\n").length} lines`} /></div>}
    </div>
  );
}
