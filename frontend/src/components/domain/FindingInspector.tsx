import { useEffect, useState } from "react";
import { GitFork, FileCode2, MessageSquareText } from "lucide-react";
import { api } from "../../api";
import { categoryLabel } from "../../lib/severity";
import { plural } from "../../lib/format";
import { useWorkspace } from "../../lib/workspace";
import type { Dossier, Finding, GraphData, SourceExcerpt } from "../../types";
import { SeverityBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Eyebrow } from "../ui/Layout";
import { CodeViewer, toLines } from "./CodeViewer";
import { EvidenceRef } from "./EvidenceRef";

const CONTEXT_LINES = 4;

interface Props {
  finding: Finding;
  dossier: Dossier;
  graph: GraphData | null;
  rejected: boolean;
}

/** Revelación progresiva: resumen → por qué importa → evidencia → impacto → acción (PRODUCT.md §21). */
export function FindingInspector({ finding, dossier, graph, rejected }: Props) {
  const { route, go, token, seedComposer } = useWorkspace();
  const [index, setIndex] = useState(0);
  const [excerpt, setExcerpt] = useState<SourceExcerpt | null>(null);
  const [excerptFailed, setExcerptFailed] = useState(false);
  const evidence = finding.evidence[index] ?? finding.evidence[0];
  const jobId = route.jobId ?? "";

  useEffect(() => setIndex(0), [finding.id]);

  useEffect(() => {
    if (!evidence || !jobId) return;
    let cancelled = false;
    setExcerpt(null);
    setExcerptFailed(false);
    api
      .source(jobId, evidence.path, Math.max(1, evidence.line_start - CONTEXT_LINES), evidence.line_end + CONTEXT_LINES, token)
      .then((data) => !cancelled && setExcerpt(data))
      .catch(() => !cancelled && setExcerptFailed(true));
    return () => {
      cancelled = true;
    };
  }, [jobId, token, evidence]);

  const check = (i: number) => dossier.evidence_checks.find((item) => item.finding_id === finding.id && item.evidence_index === i);
  const blast = graph?.blast_radius.find((item) => item.finding_id === finding.id) ?? null;
  const risk = dossier.risk_matrix.find((item) => item.finding_id === finding.id) ?? null;
  const nodeName = (id: string) => graph?.nodes.find((node) => node.id === id)?.qualname ?? id;

  return (
    <article className="space-y-5" aria-labelledby="inspector-title">
      <header>
        <div className="flex flex-wrap items-center gap-3">
          <SeverityBadge severity={finding.severity} />
          <span className="text-micro tracking-eyebrow text-subtle uppercase">{categoryLabel(finding.category)} · {finding.subcategory}</span>
          <span className="ml-auto font-mono text-caption text-subtle">{finding.id}</span>
        </div>
        <h2 id="inspector-title" className="mt-2 font-display text-title font-normal text-balance text-fg">{finding.title}</h2>
        <p className="mt-2 text-caption text-muted">
          <span className={finding.observed_or_inferred === "observed" ? "text-verified" : "text-warning"}>
            {finding.observed_or_inferred === "observed" ? "Hecho detectado" : "Inferencia"}
          </span>
          {" · "}
          {rejected ? "rechazado: su evidencia no coincide con el código" : "evidencia comprobada por el validador"}
        </p>
      </header>

      <section>
        <Eyebrow>Por qué importa</Eyebrow>
        <p className="mt-1.5 text-body text-pretty text-fg-2">{finding.explanation}</p>
      </section>

      <section>
        <Eyebrow>Evidencia · {plural(finding.evidence.length, "referencia", "referencias")}</Eyebrow>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {finding.evidence.map((item, i) => {
            const status = check(i);
            return (
              <EvidenceRef
                key={`${item.path}-${i}`}
                path={item.path}
                lineStart={item.line_start}
                lineEnd={item.line_end}
                verified={status ? status.status === "valid" : null}
                reason={status?.reason}
                active={i === index}
                onOpen={() => setIndex(i)}
              />
            );
          })}
        </div>
        {evidence && (
          <div className="mt-3">
            <CodeViewer
              path={evidence.path}
              lines={excerpt ? excerpt.lines : toLines(evidence.snippet, evidence.line_start)}
              marks={[{ start: evidence.line_start, end: evidence.line_end, severity: finding.severity, label: finding.title }]}
              caption={excerpt ? `de ${excerpt.total_lines} líneas` : excerptFailed ? "fragmento citado por Bob" : "cargando…"}
              maxHeight="18rem"
            />
          </div>
        )}
      </section>

      <section>
        <Eyebrow>Código afectado</Eyebrow>
        {!graph ? (
          <p className="mt-1.5 text-caption text-subtle">Cargando grafo de llamadas…</p>
        ) : !blast ? (
          <p className="mt-1.5 text-body text-muted">Sin cálculo de impacto para este hallazgo.</p>
        ) : (
          <div className="mt-1.5 space-y-2 text-body">
            <p className="text-fg-2">
              Origen en <span className="font-mono text-fg">{blast.origin_nodes.map(nodeName).join(", ")}</span>.{" "}
              {blast.impacted_nodes.length === 0
                ? "Ninguna otra función la llama directa o indirectamente."
                : `${plural(blast.impacted_nodes.length, "función la llama", "funciones la llaman")} directa o indirectamente.`}
            </p>
            {blast.impacted_nodes.length > 0 && (
              <ul className="flex flex-wrap gap-1.5">
                {blast.impacted_nodes.slice(0, 12).map((id) => (
                  <li key={id} className="rounded-pill border border-line px-2 py-0.5 font-mono text-caption text-fg-2">{nodeName(id)}</li>
                ))}
              </ul>
            )}
            {risk && <p className="font-mono text-caption text-subtle">Riesgo calculado: {risk.formula}</p>}
          </div>
        )}
      </section>

      <section>
        <Eyebrow>Acción recomendada</Eyebrow>
        <p className="mt-1.5 border-l-2 border-verified pl-3 text-body text-pretty text-fg">{finding.recommendation}</p>
      </section>

      <div className="flex flex-wrap gap-2 border-t border-line pt-4">
        <Button size="sm" icon={<MessageSquareText size={14} aria-hidden />} onClick={() => seedComposer(`¿Qué podría romperse si corrijo ${finding.id} (${finding.title})? ¿Qué pruebas debería ejecutar?`)}>
          Preguntar a Bob por el impacto
        </Button>
        <Button size="sm" variant="ghost" icon={<GitFork size={14} aria-hidden />} onClick={() => go("architecture", { finding: finding.id })}>
          Ver en el grafo de llamadas
        </Button>
        {evidence && (
          <Button size="sm" variant="ghost" icon={<FileCode2 size={14} aria-hidden />} onClick={() => go("repository", { file: evidence.path, line: evidence.line_start, finding: finding.id })}>
            Abrir {evidence.path}
          </Button>
        )}
      </div>
    </article>
  );
}
