import { useState } from "react";
import { views } from "../api";
import { Mermaid } from "../components/Mermaid";
import { Button, Card, EmptyState, ErrorState, FixtureNotice, Loading, ModeBadge, PageHeader } from "../components/ui";
import { pertExpected, pertStdDev } from "../lib/pert";
import type { Theme } from "../lib/theme";
import { useLoaded } from "../lib/useLoaded";
import type { ArchOption } from "../types";

const RISK: Record<ArchOption["risk"], { label: string; tone: string }> = {
  low: { label: "Riesgo bajo", tone: "text-ok bg-ok/10 ring-ok/30" },
  medium: { label: "Riesgo medio", tone: "text-warn bg-warn/10 ring-warn/30" },
  high: { label: "Riesgo alto", tone: "text-bad bg-bad/10 ring-bad/30" },
};

export function ArchitectureView({ jobId, theme, onGoHome }: { jobId: string | null; theme: Theme; onGoHome: () => void }) {
  const [tab, setTab] = useState<string | null>(null);
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
  const diagram = data.diagrams.find((item) => item.id === tab) ?? data.diagrams[0];
  const tabClass = (active: boolean) => `rounded-lg px-4 py-1.5 text-sm transition ${active ? "bg-accent text-accent-fg" : "text-muted hover:text-fg"}`;
  const totalDays = data.pert_plan.reduce((sum, phase) => sum + pertExpected(phase.optimistic_days, phase.nominal_days, phase.pessimistic_days), 0);
  const totalSd = Math.sqrt(data.pert_plan.reduce((sum, phase) => sum + pertStdDev(phase.optimistic_days, phase.pessimistic_days) ** 2, 0));

  return (
    <>
      <PageHeader title="Arquitectura" subtitle={`Del sistema actual a la arquitectura objetivo${data.selected_first_cut ? `; primer corte: ${data.selected_first_cut}` : ""}.`} right={<ModeBadge mode={data.execution_mode} />} />
      <FixtureNotice show={origin === "fixture"} />

      <Card className="p-5">
        {diagram ? (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div role="tablist" aria-label="Diagramas" className="inline-flex flex-wrap rounded-xl border border-line bg-surface-2 p-1">
                {data.diagrams.map((item) => (
                  <button key={item.id} role="tab" aria-selected={diagram.id === item.id} type="button" onClick={() => setTab(item.id)} className={tabClass(diagram.id === item.id)}>{item.label}</button>
                ))}
              </div>
              <ul className="flex flex-wrap gap-4 text-xs text-muted" aria-label="Leyenda">
                <li className="flex items-center gap-2"><span className="h-3 w-5 rounded-sm border-2 border-[#38bdf8] bg-[#0e3a4f]" aria-hidden />Observado en el código</li>
                <li className="flex items-center gap-2"><span className="h-3 w-5 rounded-sm border border-dashed border-[#c4a5ff] bg-[#2a2233]" aria-hidden />Inferido (plan, no verificado)</li>
              </ul>
            </div>
            <p className="mb-3 text-xs text-muted">
              {diagram.provenance === "observed" ? "Generado por el pipeline a partir del código real del repositorio." : "Plan derivado del corte de migración; todavía no es código en producción."}
            </p>
            <Mermaid chart={diagram.mermaid} theme={theme} />
          </>
        ) : (
          <EmptyState title="Sin diagramas">El pipeline no generó diagramas para este análisis.</EmptyState>
        )}
      </Card>

      <h2 className="mb-3 mt-8 text-sm font-semibold">Opciones de migración</h2>
      {data.options.length === 0 ? (
        <EmptyState title="Sin opciones">El pipeline no comparó opciones de migración.</EmptyState>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {data.options.map((option) => (
            <Card key={option.id} className={`flex flex-col p-5 ${option.recommended ? "border-accent/60 ring-1 ring-accent/30" : ""}`}>
              <div className="mb-2 flex items-start justify-between gap-2">
                <h3 className="font-semibold">{option.name}</h3>
                {option.recommended && <span className="shrink-0 rounded-md bg-accent px-2 py-0.5 text-[11px] font-semibold text-accent-fg">Recomendada</span>}
              </div>
              {option.pattern && <p className="text-sm text-muted">{option.pattern}</p>}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className={`rounded-md px-2 py-0.5 text-xs ring-1 ring-inset ${RISK[option.risk].tone}`}>{RISK[option.risk].label}</span>
                <span className="rounded-md bg-surface-2 px-2 py-0.5 font-mono text-xs">{option.effort_days} días</span>
              </div>
              {option.target_stack && <p className="mt-2 text-xs text-muted">Stack destino: {option.target_stack}</p>}
              <ul className="mt-3 space-y-1 text-sm">
                {option.pros.map((item) => <li key={item} className="text-ok">+ <span className="text-fg">{item}</span></li>)}
                {option.cons.map((item) => <li key={item} className="text-bad">− <span className="text-fg">{item}</span></li>)}
              </ul>
            </Card>
          ))}
        </div>
      )}

      {data.pert_plan.length > 0 && (
        <>
          <h2 className="mb-3 mt-8 text-sm font-semibold">Plan y esfuerzo PERT</h2>
          <Card className="overflow-x-auto">
            <table className="w-full min-w-160 text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-medium">Fase</th>
                  <th className="px-3 py-3 text-right font-medium">O</th>
                  <th className="px-3 py-3 text-right font-medium">M</th>
                  <th className="px-3 py-3 text-right font-medium">P</th>
                  <th className="px-4 py-3 text-right font-medium">Esperado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.pert_plan.map((phase) => (
                  <tr key={phase.phase_number}>
                    <td className="px-4 py-3"><p className="font-medium">{phase.name}</p><p className="text-xs text-muted">Reversa: {phase.rollback_strategy}</p></td>
                    <td className="px-3 py-3 text-right font-mono">{phase.optimistic_days}</td>
                    <td className="px-3 py-3 text-right font-mono">{phase.nominal_days}</td>
                    <td className="px-3 py-3 text-right font-mono">{phase.pessimistic_days}</td>
                    <td className="px-4 py-3 text-right font-mono font-semibold">{pertExpected(phase.optimistic_days, phase.nominal_days, phase.pessimistic_days).toFixed(1)} d</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-line bg-surface-2">
                  <td className="px-4 py-3 font-semibold" colSpan={4}>Total <span className="text-xs font-normal text-muted">(± {totalSd.toFixed(1)} d, desviación combinada)</span></td>
                  <td className="px-4 py-3 text-right font-mono font-semibold text-accent">{totalDays.toFixed(1)} d</td>
                </tr>
              </tfoot>
            </table>
          </Card>
          <p className="mt-3 text-xs text-muted">O, M y P son días optimista, probable y pesimista. El esperado ((O + 4M + P) / 6) lo calcula el código; no lo inventa la IA.</p>
        </>
      )}
    </>
  );
}
