import { useState } from "react";
import { views } from "../api";
import { Mermaid } from "../components/Mermaid";
import { Button, Card, EmptyState, ErrorState, FixtureNotice, Loading, ModeBadge, PageHeader } from "../components/ui";
import { pertExpected, pertStdDev } from "../lib/pert";
import type { Theme } from "../lib/theme";
import { useLoaded } from "../lib/useLoaded";
import type { MigrationOption } from "../types";

const RISK: Record<MigrationOption["risk"], { label: string; tone: string }> = {
  low: { label: "Riesgo bajo", tone: "text-ok bg-ok/10 ring-ok/30" },
  medium: { label: "Riesgo medio", tone: "text-warn bg-warn/10 ring-warn/30" },
  high: { label: "Riesgo alto", tone: "text-bad bg-bad/10 ring-bad/30" },
};

export function ArchitectureView({ jobId, theme, onGoHome }: { jobId: string | null; theme: Theme; onGoHome: () => void }) {
  const [tab, setTab] = useState<"current" | "target">("current");
  const { result, error, retry, loading } = useLoaded(views.architecture, jobId);

  if (!jobId) {
    return (
      <>
        <PageHeader title="Arquitectura" />
        <EmptyState title="Aún no hay arquitectura" action={<Button onClick={onGoHome}>Ir a Inicio</Button>}>
          Lanza una auditoría para ver la arquitectura actual y la objetivo.
        </EmptyState>
      </>
    );
  }
  if (error) return <><PageHeader title="Arquitectura" /><ErrorState message={error} onRetry={retry} /></>;
  if (loading || !result) return <><PageHeader title="Arquitectura" /><Loading /></>;

  const { data, origin } = result;
  const tabClass = (active: boolean) => `rounded-lg px-4 py-1.5 text-sm transition ${active ? "bg-accent text-accent-fg" : "text-muted hover:text-fg"}`;

  return (
    <>
      <PageHeader title="Arquitectura" subtitle="Del sistema actual a la arquitectura objetivo, con las opciones de migración y su esfuerzo." right={<ModeBadge mode={data.execution_mode} />} />
      <FixtureNotice show={origin === "fixture"} />

      <Card className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div role="tablist" aria-label="Arquitectura" className="inline-flex rounded-xl border border-line bg-surface-2 p-1">
            <button role="tab" aria-selected={tab === "current"} type="button" onClick={() => setTab("current")} className={tabClass(tab === "current")}>Actual</button>
            <button role="tab" aria-selected={tab === "target"} type="button" onClick={() => setTab("target")} className={tabClass(tab === "target")}>Objetivo</button>
          </div>
          <ul className="flex flex-wrap gap-4 text-xs text-muted" aria-label="Leyenda">
            <li className="flex items-center gap-2"><span className="h-3 w-5 rounded-sm border-2 border-[#38bdf8] bg-[#0e3a4f]" aria-hidden />Observado en el código</li>
            <li className="flex items-center gap-2"><span className="h-3 w-5 rounded-sm border border-dashed border-[#c4a5ff] bg-[#2a2233]" aria-hidden />Inferido (no verificado)</li>
          </ul>
        </div>
        <Mermaid chart={tab === "current" ? data.current_mermaid : data.target_mermaid} theme={theme} />
      </Card>

      <h2 className="mb-3 mt-8 text-sm font-semibold">Opciones de migración</h2>
      <div className="grid gap-4 lg:grid-cols-3">
        {data.options.map((option) => {
          const { optimistic: o, likely: m, pessimistic: p } = option.effort_hours;
          return (
            <Card key={option.id} className={`flex flex-col p-5 ${option.recommended ? "border-accent/60 ring-1 ring-accent/30" : ""}`}>
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="font-semibold">{option.name}</h3>
                {option.recommended && <span className="rounded-md bg-accent px-2 py-0.5 text-[11px] font-semibold text-accent-fg">Recomendada</span>}
              </div>
              <p className="text-sm text-muted">{option.summary}</p>
              <span className={`mt-3 w-fit rounded-md px-2 py-0.5 text-xs ring-1 ring-inset ${RISK[option.risk].tone}`}>{RISK[option.risk].label}</span>
              <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                {([["Optimista", o], ["Probable", m], ["Pesimista", p]] as const).map(([label, value]) => (
                  <div key={label} className="rounded-lg bg-surface-2 py-2">
                    <dt className="text-muted">{label}</dt>
                    <dd className="font-mono text-sm">{value} h</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-3 text-sm">
                Esfuerzo PERT: <strong className="font-mono">{pertExpected(o, m, p).toFixed(0)} h</strong>{" "}
                <span className="text-xs text-muted">± {pertStdDev(o, p).toFixed(0)} h</span>
              </p>
              <ul className="mt-3 space-y-1 text-sm">
                {option.pros.map((item) => <li key={item} className="text-ok">+ <span className="text-fg">{item}</span></li>)}
                {option.cons.map((item) => <li key={item} className="text-bad">− <span className="text-fg">{item}</span></li>)}
              </ul>
            </Card>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-muted">El esfuerzo PERT ((O + 4M + P) / 6) lo calcula el código a partir de las estimaciones; no lo inventa la IA.</p>
    </>
  );
}
