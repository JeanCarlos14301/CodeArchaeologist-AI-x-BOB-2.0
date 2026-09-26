import { useState } from "react";
import { Download, Hammer } from "lucide-react";
import { Button } from "../../ui/Button";
import { Eyebrow } from "../../ui/Layout";
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
  done: { glyph: "✓", label: "hecho", tone: "text-verified" },
  failed: { glyph: "✗", label: "falló", tone: "text-danger" },
  skipped: { glyph: "○", label: "omitido", tone: "text-subtle" },
} as const;

export function ImplementationPanel({ plan, state, busy, onImplement, onDownload, loadDiff }: Props) {
  const [understood, setUnderstood] = useState(false);
  const running = state.phase === "implementing";
  const result = state.implementation;
  const started = running || result !== null;

  return (
    <div>
      {!started && (
        <div className="grid gap-x-10 gap-y-5 @3xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div>
            <p className="text-body text-pretty text-fg">
              Bob ejecutará los {plan.steps.length} pasos en orden sobre una <strong className="font-medium">copia</strong> del proyecto y te devolverá un ZIP con el resultado y el diff completo.
            </p>
            <ul className="mt-3 space-y-1.5 text-caption text-muted">
              <li className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-verified">✓</span><span>Tu proyecto original no se modifica.</span></li>
              <li className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-verified">✓</span><span>Bob no ejecuta comandos ni el código del proyecto.</span></li>
              <li className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-warning">▲</span><span>El resultado es un borrador: solo se comprueba su sintaxis, no se prueba. Revísalo antes de usarlo.</span></li>
            </ul>
          </div>
          <div className="flex flex-col justify-end gap-4">
            <label className="flex cursor-pointer items-start gap-3 text-body text-fg-2">
              <input type="checkbox" checked={understood} onChange={(event) => setUnderstood(event.target.checked)} className="mt-1 h-4 w-4 accent-[var(--ca-signal-orange)]" />
              <span>Entiendo que Bob va a escribir código nuevo y que debo revisarlo y probarlo yo.</span>
            </label>
            <div><Button variant="primary" disabled={!understood || busy} onClick={onImplement} icon={<Hammer size={14} aria-hidden />}>Implementar el plan con Bob</Button></div>
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
  const events = state.events.filter((event) => event.phase === "implementing").slice(-6);
  const currentId = running ? events.filter((event) => event.step_id).slice(-1)[0]?.step_id ?? null : null;
  return (
    <div className="grid gap-x-10 gap-y-5 @3xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]" aria-live="polite">
      <div>
        <Eyebrow>Pasos</Eyebrow>
        <ol className="mt-2 divide-y divide-line-subtle border-y border-line-subtle">
          {plan.steps.map((step, index) => {
            const run = runs.get(step.id);
            const live = running && step.id === currentId && !run;
            return (
              <li key={step.id} className="grid grid-cols-[1.75rem_minmax(0,1fr)_auto] items-baseline gap-2 py-2 text-caption">
                <span className={`font-mono ${run ? STATUS[run.status].tone : live ? "text-activity" : "text-subtle"}`}>
                  {run ? STATUS[run.status].glyph : live ? <span aria-hidden className="inline-block h-1.5 w-1.5 animate-pulse rounded-pill bg-activity" /> : String(index + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 truncate text-body text-fg-2">{step.title}{run?.note && <span className="block truncate text-caption text-subtle" title={run.note}>{run.note}</span>}</span>
                <span className="font-mono text-subtle tabular-nums">{run ? `${run.changed.length} arch.` : live ? "en curso" : ""}</span>
              </li>
            );
          })}
        </ol>
      </div>
      <div>
        <Eyebrow>Actividad</Eyebrow>
        <ul className="mt-2 space-y-1.5 text-caption text-muted">
          {events.length === 0 && <li className="text-subtle">Esperando a Bob…</li>}
          {events.map((event) => <li key={`${event.t}-${event.message}`} className="grid grid-cols-[1rem_1fr]"><span aria-hidden className="text-subtle">·</span><span>{event.message}</span></li>)}
        </ul>
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
          <Eyebrow>Resultado</Eyebrow>
          <p className="mt-1 font-mono text-body text-fg tabular-nums">
            {result.files_changed} archivos · <span className="text-verified">+{result.lines_added}</span> <span className="text-danger">−{result.lines_removed}</span> líneas
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => void toggleDiff()}>{diff === null ? "Ver diff" : "Ocultar diff"}</Button>
          <Button variant="secondary" onClick={() => void download("migration.diff")}>Descargar diff</Button>
          <Button variant="primary" onClick={() => void download("modernized.zip")} icon={<Download size={14} aria-hidden />}>Descargar proyecto migrado (ZIP)</Button>
        </div>
      </div>
      {error && <p role="alert" className="mt-3 text-caption text-danger">{error}</p>}

      <ul className="mt-5 space-y-2 text-body text-fg-2">
        <li className="grid grid-cols-[1.25rem_1fr]">
          <span aria-hidden className={bad.length ? "text-danger" : "text-verified"}>{bad.length ? "✗" : "✓"}</span>
          <span>{result.checks.length === 0 ? "No hubo archivos de Python, JSON, YAML o TOML cuya sintaxis comprobar." : bad.length ? `${bad.length} de ${result.checks.length} archivos comprobados tienen errores de sintaxis.` : `Sintaxis correcta en los ${result.checks.length} archivos comprobables.`}</span>
        </li>
        {bad.map((check) => <li key={check.path} className="ml-5 font-mono text-caption text-danger">{check.path} <span className="font-sans text-subtle">· {check.detail}</span></li>)}
        {result.outside_plan.length > 0 && (
          <li className="grid grid-cols-[1.25rem_1fr]">
            <span aria-hidden className="text-warning">▲</span>
            <span>Bob tocó {result.outside_plan.length} {result.outside_plan.length === 1 ? "archivo" : "archivos"} que no estaban en el plan: <span className="font-mono text-caption">{result.outside_plan.slice(0, 6).join(", ")}{result.outside_plan.length > 6 ? "…" : ""}</span>. Revísalos.</span>
          </li>
        )}
        {failedStep && (
          <li className="grid grid-cols-[1.25rem_1fr]">
            <span aria-hidden className="text-danger">✗</span>
            <span>Un paso falló y los siguientes se omitieron: el ZIP contiene solo lo que se alcanzó a hacer. <button type="button" disabled={busy} onClick={onRetry} className="text-fg underline underline-offset-2">Volver a intentarlo</button></span>
          </li>
        )}
        <li className="grid grid-cols-[1.25rem_1fr] text-caption text-subtle"><span aria-hidden>○</span><span>{result.not_executed}</span></li>
      </ul>

      {diff !== null && <div className="mt-5"><CodeViewer path="migration.diff" lines={toLines(diff)} maxHeight="28rem" caption={`${diff.split("\n").length} líneas`} /></div>}
    </div>
  );
}
