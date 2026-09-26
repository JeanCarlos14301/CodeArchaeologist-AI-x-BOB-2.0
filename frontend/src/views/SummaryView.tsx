import { Button, Card, EmptyState, ModeBadge, PageHeader, SEVERITY_BAR, SEVERITY_LABEL, SEVERITY_ORDER, SeverityBadge } from "../components/ui";
import type { Dossier, Severity } from "../types";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-[11px] uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </Card>
  );
}

interface Props {
  dossier: Dossier | null;
  onOpenFinding: (id: string) => void;
  onGoHome: () => void;
  onOpenFindings: () => void;
}

export function SummaryView({ dossier, onOpenFinding, onGoHome, onOpenFindings }: Props) {
  if (!dossier) {
    return (
      <>
        <PageHeader title="Resumen" />
        <EmptyState icon="◌" title="Aún no hay un expediente" action={<Button onClick={onGoHome}>Ir a Inicio</Button>}>
          Lanza una auditoría para ver aquí el resumen del análisis.
        </EmptyState>
      </>
    );
  }

  const { stats, findings } = dossier;
  const counts = Object.fromEntries(SEVERITY_ORDER.map((s) => [s, findings.filter((f) => f.severity === s).length])) as Record<Severity, number>;
  const categories = [...new Set(findings.map((f) => f.category))].map((category) => ({ category, count: findings.filter((f) => f.category === category).length })).sort((a, b) => b.count - a.count);
  const top = [...findings].sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)).slice(0, 3);

  return (
    <>
      <PageHeader
        title={`Resumen · ${dossier.repo_name}`}
        subtitle={`Generado el ${new Date(dossier.generated_at).toLocaleString()}. Todas las cifras las calcula el pipeline en Python, no la IA.`}
        right={<ModeBadge mode={dossier.execution_mode} />}
      />

      {findings.length === 0 ? (
        <EmptyState icon="✓" title="Sin hallazgos" action={<Button variant="ghost" onClick={onGoHome}>Analizar otro repositorio</Button>}>
          Bob no reportó problemas con evidencia verificable en este repositorio.
          {dossier.rejected_findings.length > 0 && ` El validador descartó ${dossier.rejected_findings.length} hallazgos por evidencia que no coincide con el código.`}
        </EmptyState>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Hallazgos validados" value={`${stats.findings_validated}/${stats.findings_reported}`} hint="Con evidencia verificada" />
            <Stat label="Evidencias válidas" value={`${Math.round(stats.evidence_valid_ratio * 100)}%`} hint={`${stats.evidence_valid} de ${stats.evidence_total}`} />
            {stats.pipeline_ms != null ? (
              <Stat label="Duración del pipeline" value={`${(stats.pipeline_ms / 1000).toFixed(1)} s`} hint="Suma de las 11 etapas" />
            ) : (
              <Stat label="Coste Bob" value={stats.bob_cost == null ? "—" : `${stats.bob_cost.toFixed(2)} bc`} hint="bobcoins" />
            )}
            <Stat label="Duración Bob" value={stats.bob_duration_ms == null ? "—" : `${Math.round(stats.bob_duration_ms / 1000)} s`} />
          </div>

          {dossier.snapshot && (
            <p className="text-xs text-muted">
              Repositorio analizado: {dossier.snapshot.total_files} archivos · {dossier.snapshot.total_loc} líneas · {dossier.snapshot.languages.join(", ")} · huella <span className="font-mono">{dossier.snapshot.sha256.slice(0, 12)}</span>
            </p>
          )}
          {dossier.executive_summary && (
            <Card className="p-5">
              <h2 className="mb-2 text-sm font-semibold">Resumen ejecutivo</h2>
              <p className="whitespace-pre-line text-sm leading-relaxed text-muted">{dossier.executive_summary}</p>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-5">
              <h2 className="mb-4 text-sm font-semibold">Por severidad</h2>
              <ul className="space-y-3">
                {SEVERITY_ORDER.map((severity) => (
                  <li key={severity} className="flex items-center gap-3 text-sm">
                    <span className="w-16 text-muted">{SEVERITY_LABEL[severity]}</span>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-2">
                      <div className={`h-full rounded-full ${SEVERITY_BAR[severity]}`} style={{ width: `${(counts[severity] / findings.length) * 100}%` }} />
                    </div>
                    <span className="w-6 text-right font-mono tabular-nums">{counts[severity]}</span>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-5">
              <h2 className="mb-4 text-sm font-semibold">Por categoría</h2>
              <ul className="flex flex-wrap gap-2">
                {categories.map(({ category, count }) => (
                  <li key={category} className="rounded-lg border border-line bg-surface-2 px-3 py-1.5 text-sm">
                    {category} <span className="ml-1 font-mono text-accent">{count}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Riesgos principales</h2>
              <Button variant="ghost" onClick={onOpenFindings}>Ver los {findings.length} hallazgos</Button>
            </div>
            <ul className="divide-y divide-line">
              {top.map((finding) => (
                <li key={finding.id}>
                  <button type="button" onClick={() => onOpenFinding(finding.id)} className="flex w-full items-center gap-3 py-3 text-left hover:text-accent">
                    <SeverityBadge severity={finding.severity} />
                    <span className="min-w-0 flex-1 truncate text-sm">{finding.title}</span>
                    <span className="hidden font-mono text-xs text-muted sm:inline">{finding.evidence[0].path}:{finding.evidence[0].line_start}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </>
  );
}
