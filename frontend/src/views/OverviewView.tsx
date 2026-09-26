import { ArrowRight } from "lucide-react";
import { PertRange } from "../components/domain/PertRange";
import { ModeBadge, SeverityBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataList, Meter, ScreenHeader, Section } from "../components/ui/Layout";
import { formatCost, formatDate, formatPercent, formatSeconds, lineRange } from "../lib/format";
import { bySeverity, countBySeverity } from "../lib/severity";
import { detectStack } from "../lib/stack";
import { useResource, useWorkspace } from "../lib/workspace";
import type { Dossier } from "../types";
import { JobGate } from "./JobGate";

export function OverviewView() {
  return <JobGate>{(dossier) => <Overview dossier={dossier} />}</JobGate>;
}

function Overview({ dossier }: { dossier: Dossier }) {
  const { go } = useWorkspace();
  const architecture = useResource("architecture");
  const requirements = useResource("requirements");
  const arch = architecture.data;
  const stack = detectStack(arch, requirements.data ?? []);
  const counts = countBySeverity(dossier.findings);
  const top = [...dossier.findings].sort(bySeverity).slice(0, 5);
  const tests = dossier.migration?.tests ?? [];
  const passed = (target: "legacy" | "modern") => tests.filter((t) => t.target === target && t.status === "passed").length;
  const total = (target: "legacy" | "modern") => tests.filter((t) => t.target === target).length;
  const stackLine = [stack.language, ...stack.frameworks, stack.data].filter(Boolean).join(" · ");

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Resumen · ¿Qué tipo de sistema es?"
        title={dossier.repo_name}
        description={stackLine ? `${stackLine}${arch ? ` · ${arch.totals.files} archivos Python · ${arch.totals.functions} funciones · ${arch.routes.length} rutas HTTP` : ""}` : "Detectando stack…"}
        meta={<>
          <ModeBadge mode={dossier.execution_mode} />
          <span>Generado {formatDate(dossier.generated_at)}</span>
          <span>Stack detectado en requirements.txt, AST y SQL del propio repositorio</span>
        </>}
        actions={<Button variant="secondary" onClick={() => go("risks")} icon={<ArrowRight size={14} aria-hidden />}>Revisar {dossier.findings.length} riesgos</Button>}
      />

      <div className="grid gap-x-12 @3xl:grid-cols-2">
        <Section eyebrow="Salud" title="Qué encontró el análisis">
          <DataList rows={[
            { label: "Hallazgos con evidencia verificada", value: `${dossier.stats.findings_validated}/${dossier.stats.findings_reported}`, hint: dossier.rejected_findings.length ? `${dossier.rejected_findings.length} descartados por el validador` : "ninguno descartado" },
            { label: <SeverityBadge severity="critical" />, value: counts.critical },
            { label: <SeverityBadge severity="high" />, value: counts.high },
            { label: <SeverityBadge severity="medium" />, value: counts.medium },
            { label: <SeverityBadge severity="low" />, value: counts.low },
            { label: "Dependencias circulares", value: arch ? arch.circular_dependencies.length : "…" },
            { label: "SQL construido por concatenación", value: arch ? `${arch.sql.concatenated} de ${arch.sql.total}` : "…" },
          ]} />
        </Section>

        <Section eyebrow="Preparación" title="Qué tan listo está para modernizar">
          <div className="space-y-5">
            <Meter label="Evidencia verificada por código" value={dossier.stats.evidence_valid} max={dossier.stats.evidence_total} tone="bg-verified"
              detail={`${formatPercent(dossier.stats.evidence_valid_ratio)} de las citas de Bob existen en el repositorio.`} />
            {arch && <Meter label="Consultas SQL parametrizadas" value={arch.sql.parameterized} max={arch.sql.total} tone="bg-fg"
              detail={arch.sql.total ? "El resto se arma por concatenación de texto." : "No se detectaron consultas SQL."} />}
            <Meter label="Pruebas de caracterización · legado" value={passed("legacy")} max={total("legacy")} tone="bg-verified"
              detail={total("legacy") ? "Fijan el comportamiento actual del endpoint del primer corte." : "No se ejecutaron: el código subido nunca se ejecuta."} />
            <Meter label="Pruebas de caracterización · moderno" value={passed("modern")} max={total("modern")} tone="bg-verified" />
          </div>
        </Section>
      </div>

      <Section eyebrow="Riesgos principales" title="Lo que más puede complicar la migración" aside={<button type="button" className="text-caption text-fg-2 hover:text-fg" onClick={() => go("risks")}>Ver los {dossier.findings.length} →</button>}>
        <ul className="divide-y divide-line-subtle border-y border-line-subtle">
          {top.map((finding) => (
            <li key={finding.id}>
              <button type="button" onClick={() => go("risks", { finding: finding.id })} className="grid w-full grid-cols-[7rem_1fr_auto] items-baseline gap-4 py-3 text-left hover:bg-raised">
                <SeverityBadge severity={finding.severity} />
                <span className="text-body text-fg">{finding.title}</span>
                <span className="hidden font-mono text-caption text-subtle md:inline">{finding.evidence[0].path}:{lineRange(finding.evidence[0].line_start, finding.evidence[0].line_end)}</span>
              </button>
            </li>
          ))}
        </ul>
      </Section>

      <div className="grid gap-x-12 @3xl:grid-cols-2">
        <Section eyebrow="Primer corte" title={dossier.migration ? `Migrar ${dossier.migration.endpoint}` : "Estimación del primer corte"}>
          {dossier.first_cut_pert ? (
            <>
              <PertRange pert={dossier.first_cut_pert} />
              <Button size="sm" variant="secondary" className="mt-5" onClick={() => go("modernization")}>Ver plan de modernización</Button>
            </>
          ) : (
            <p className="text-body text-muted">No hay estimación PERT para este análisis.</p>
          )}
        </Section>

        <Section eyebrow="Trazabilidad" title="De dónde salen estas cifras">
          <DataList rows={[
            { label: "Análisis", value: dossier.job_id ?? "—" },
            { label: "SHA-256 del código", value: <span title={dossier.source_sha256 ?? ""}>{dossier.source_sha256 ? `${dossier.source_sha256.slice(0, 16)}…` : "—"}</span> },
            { label: "Tarea de IBM Bob", value: dossier.bob_task_id ? `${dossier.bob_task_id.slice(0, 12)}…` : "—" },
            { label: "Coste · duración de Bob", value: `${formatCost(dossier.stats.bob_cost)} · ${formatSeconds(dossier.stats.bob_duration_ms)}` },
            { label: "Contrato", value: `schema v${dossier.schema_version}` },
          ]} />
          <p className="mt-3 text-caption text-subtle">Las cifras las calcula el pipeline en Python; Bob solo aporta hallazgos, y cada uno se verifica.</p>
        </Section>
      </div>
    </div>
  );
}
