import { ArrowRight } from "lucide-react";
import type { ActivityModel } from "../../../lib/activity";
import { formatCost, formatSeconds, lineRange, plural } from "../../../lib/format";
import { SEVERITY, SEVERITY_ORDER } from "../../../lib/severity";
import type { Severity } from "../../../types";
import { SeverityBadge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { Eyebrow } from "../../ui/Layout";

/** Etapa 1: controles de seguridad del ZIP e inventario del sandbox (qué contiene el repositorio). */
export function PreparingPanel({ model }: { model: ActivityModel }) {
  const inventory = model.inventory;
  const maxLanguage = Math.max(1, ...(inventory?.languages.map((item) => item.files) ?? [1]));
  return (
    <div className="space-y-6">
      <section aria-label="Controles de seguridad">
        <Eyebrow>Controles de seguridad</Eyebrow>
        {model.checks.length === 0 ? (
          <p className="mt-2 text-body text-muted">Muestra registrada del equipo: se copia desde el servidor, sin ZIP que validar. El código nunca se ejecuta en esta etapa.</p>
        ) : (
          <ul className="mt-2 divide-y divide-line-subtle">
            {model.checks.map((check) => (
              <li key={check.name} className="grid animate-enter grid-cols-[1rem_1fr_auto] items-baseline gap-x-3 py-2">
                <span aria-hidden className="text-verified">✓</span>
                <span className="text-body text-fg-2">{check.name}</span>
                <span className="text-right font-mono text-caption text-fg">
                  {check.value} <span className="text-subtle">{check.limit}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {!inventory ? (
        <p className="text-caption text-subtle">Copiando el repositorio al sandbox…</p>
      ) : (
        <section aria-label="Inventario del repositorio" className="space-y-5">
          <dl className="grid grid-cols-3 gap-x-6">
            {[
              ["Archivos", inventory.files.toLocaleString("es")],
              ["Líneas Python", inventory.python_lines.toLocaleString("es")],
              ["Tamaño", `${(inventory.bytes / 1024).toFixed(0)} KB`],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-micro tracking-eyebrow text-subtle uppercase">{label}</dt>
                <dd className="mt-1 font-display text-heading text-fg tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
          <div>
            <Eyebrow>Lenguajes por archivo</Eyebrow>
            <ul className="mt-2 space-y-1.5">
              {inventory.languages.map((language) => (
                <li key={language.name} className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-3 text-caption">
                  <span className="text-fg-2">{language.name}</span>
                  <span className="h-1 overflow-hidden rounded-pill bg-raised">
                    <span className="block h-full rounded-pill bg-fg-2" style={{ width: `${(language.files / maxLanguage) * 100}%` }} />
                  </span>
                  <span className="text-right font-mono text-fg tabular-nums">{language.files}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid gap-5 @2xl:grid-cols-2">
            <div>
              <Eyebrow>Carpetas principales</Eyebrow>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {inventory.top_dirs.map((dir) => (
                  <li key={dir.name} className="rounded-pill border border-line px-2.5 py-0.5 font-mono text-caption text-fg-2">
                    {dir.name} <span className="text-subtle">{dir.files}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <Eyebrow>Fuera del sandbox</Eyebrow>
              <p className="mt-2 font-mono text-caption text-subtle">{inventory.excluded.join(" · ")}</p>
            </div>
          </div>
          <p className="font-mono text-caption text-subtle">sha256 {inventory.sha256}</p>
        </section>
      )}
    </div>
  );
}

/** Etapa 3: cada cita de Bob comprobada contra el código (archivo, líneas, fragmento). */
export function ValidationPanel({ model }: { model: ActivityModel }) {
  const { checks, summary } = model.evidence;
  const valid = checks.filter((check) => check.status === "valid").length;
  const invalid = checks.length - valid;
  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 @2xl:grid-cols-4">
        {[
          ["Citas verificadas", <span key="v" className="text-verified">✓ {valid}</span>],
          ["No coinciden", <span key="i" className={invalid ? "text-danger" : "text-subtle"}>✗ {invalid}</span>],
          ["Hallazgos aceptados", summary ? summary.accepted : "…"],
          ["Descartados", summary ? summary.rejected : "…"],
        ].map(([label, value]) => (
          <div key={String(label)}>
            <dt className="text-micro tracking-eyebrow text-subtle uppercase">{label}</dt>
            <dd className="mt-1 font-mono text-body text-fg tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      {checks.length === 0 ? (
        <p className="text-body text-muted">Esperando las citas de Bob…</p>
      ) : (
        <ul aria-label="Citas comprobadas" className="grid gap-x-6 @3xl:grid-cols-2">
          {checks.map((check) => (
            <li key={check.seq} className="grid animate-enter grid-cols-[1rem_2.75rem_1fr] items-baseline gap-x-2 border-b border-line-subtle py-2 text-caption">
              <span aria-hidden className={check.status === "valid" ? "text-verified" : "text-danger"}>{check.status === "valid" ? "✓" : "✗"}</span>
              <span className={`font-mono ${check.severity ? SEVERITY[check.severity as Severity].text : "text-subtle"}`}>{check.findingId}</span>
              <span className="min-w-0">
                <span className="block truncate font-mono text-fg">{check.path}{check.lineStart ? `:${lineRange(check.lineStart, check.lineEnd ?? check.lineStart)}` : ""}</span>
                <span className="block truncate text-subtle">{check.reason}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {summary && (
        <p className="text-caption text-subtle">
          Con la evidencia aceptada, Python calculó el riesgo de {plural(summary.riskScored, "hallazgo", "hallazgos")}
          {summary.pertDays != null && <> y la estimación PERT del primer corte (<span className="font-mono text-fg-2">{summary.pertDays.toFixed(1)} días</span>)</>}.
        </p>
      )}
    </div>
  );
}

/** Etapa 4: pruebas de caracterización del primer corte, o por qué no se ejecutan. */
export function TestsPanel({ model }: { model: ActivityModel }) {
  const { tests, skipped, summary } = model.migration;
  if (skipped) {
    return (
      <div className="rounded-panel border border-dashed border-line-strong px-5 py-5">
        <p className="text-body text-fg">No se ejecutó un primer corte</p>
        <p className="mt-1 text-body text-muted">{skipped} El corte probado existe para las muestras registradas del equipo.</p>
      </div>
    );
  }
  if (tests.length === 0) return <p className="text-body text-muted">Preparando el sandbox de pruebas…</p>;
  return (
    <div className="space-y-5">
      {(["legacy", "modern"] as const).map((target) => {
        const group = tests.filter((test) => test.target === target);
        if (group.length === 0) return null;
        return (
          <section key={target} aria-label={target === "legacy" ? "Contra el legado" : "Contra el corte moderno"}>
            <Eyebrow>{target === "legacy" ? "Contra el legado" : "Contra el corte moderno"}</Eyebrow>
            <ul className="mt-2 divide-y divide-line-subtle">
              {group.map((test) => (
                <li key={test.seq} className="grid animate-enter grid-cols-[1rem_1fr_auto] items-baseline gap-x-3 py-2 text-caption">
                  <span aria-hidden className={test.status === "passed" ? "text-verified" : test.status === "failed" ? "text-danger" : "text-subtle"}>
                    {test.status === "passed" ? "✓" : test.status === "failed" ? "✗" : "○"}
                  </span>
                  <span className="truncate font-mono text-fg-2">{test.name}{test.reason && <span className="block text-danger">{test.reason}</span>}</span>
                  <span className="font-mono text-subtle tabular-nums">{Math.round(test.durationMs)} ms</span>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {summary && (
        <p className={`text-body ${summary.status === "passed" ? "text-verified" : "text-danger"}`}>
          {summary.status === "passed" ? "✓ Mismo comportamiento observable en legado y moderno" : "✗ El corte moderno no reproduce el comportamiento"} · <span className="font-mono">{summary.endpoint}</span>
        </p>
      )}
    </div>
  );
}

/** Etapa 5: el expediente y el siguiente paso. */
export function ReadyPanel({ model, onOpenSummary, onOpenRisks }: { model: ActivityModel; onOpenSummary: () => void; onOpenRisks: () => void }) {
  const done = model.done;
  if (!done) return <p className="text-body text-muted">El expediente aparecerá cuando termine la validación.</p>;
  return (
    <div className="space-y-5">
      <p className="font-display text-heading text-fg">{plural(done.findings, "hallazgo", "hallazgos")} con evidencia verificada</p>
      <ul className="flex flex-wrap gap-x-6 gap-y-2">
        {SEVERITY_ORDER.filter((severity) => done.bySeverity[severity]).map((severity) => (
          <li key={severity} className="flex items-center gap-2">
            <SeverityBadge severity={severity} />
            <span className="font-mono text-body text-fg tabular-nums">{done.bySeverity[severity]}</span>
          </li>
        ))}
      </ul>
      <p className="font-mono text-caption text-subtle">
        {done.evidenceValid}/{done.evidenceTotal} citas verificadas · IBM Bob {formatCost(done.cost)} · {formatSeconds(done.durationMs)}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button onClick={onOpenRisks} icon={<ArrowRight size={14} aria-hidden />}>Revisar los {done.findings} riesgos</Button>
        <Button variant="ghost" onClick={onOpenSummary}>Abrir el resumen del sistema</Button>
      </div>
    </div>
  );
}
