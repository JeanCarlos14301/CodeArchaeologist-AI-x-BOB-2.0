import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { CodeBlock, toLines } from "../components/CodeBlock";
import { Button, Card, EmptyState, PageHeader, SEVERITY_LABEL, SEVERITY_ORDER, SeverityBadge } from "../components/ui";
import type { Dossier, Evidence, Finding, Severity, SourceExcerpt } from "../types";

const CONTEXT_LINES = 6;

interface Selection {
  finding: Finding;
  index: number;
}

function EvidenceViewer({ jobId, token, selection, dossier }: { jobId: string; token: string; selection: Selection | null; dossier: Dossier }) {
  const [excerpt, setExcerpt] = useState<SourceExcerpt | null>(null);
  const [failed, setFailed] = useState(false);
  const evidence: Evidence | undefined = selection?.finding.evidence[selection.index];

  useEffect(() => {
    setExcerpt(null);
    setFailed(false);
    if (!evidence) return;
    let cancelled = false;
    api
      .source(jobId, evidence.path, Math.max(1, evidence.line_start - CONTEXT_LINES), evidence.line_end + CONTEXT_LINES, token)
      .then((data) => !cancelled && setExcerpt(data))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [jobId, token, evidence]);

  if (!selection || !evidence) {
    return <EmptyState icon="‹/›" title="Elige una evidencia">Cada hallazgo tiene chips con archivo y línea: al pulsarlos verás aquí el código citado.</EmptyState>;
  }

  const check = dossier.evidence_checks.find((item) => item.finding_id === selection.finding.id && item.evidence_index === selection.index);
  const range: [number, number] = [evidence.line_start, evidence.line_end];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded-md px-2 py-0.5 font-semibold ring-1 ring-inset ${check?.status === "valid" ? "bg-ok/10 text-ok ring-ok/30" : "bg-bad/10 text-bad ring-bad/30"}`}>
          {check?.status === "valid" ? "✓ Evidencia verificada por código" : "✗ Evidencia no verificada"}
        </span>
        {check && <span className="text-muted">{check.reason}</span>}
      </div>
      {excerpt ? (
        <CodeBlock path={excerpt.path} lines={excerpt.lines} highlight={range} caption={`líneas ${evidence.line_start}–${evidence.line_end} de ${excerpt.total_lines}`} />
      ) : (
        <>
          {failed ? <p className="text-xs text-muted">No se pudo leer el archivo completo; se muestra el fragmento citado por Bob.</p> : <p className="text-xs text-muted">Cargando código…</p>}
          <CodeBlock path={evidence.path} lines={toLines(evidence.snippet, evidence.line_start)} highlight={range} caption="fragmento citado" />
        </>
      )}
    </div>
  );
}

interface Props {
  jobId: string;
  token: string;
  dossier: Dossier | null;
  focusId: string | null;
  onGoHome: () => void;
}

export function FindingsView({ jobId, token, dossier, focusId, onGoHome }: Props) {
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [query, setQuery] = useState("");
  const [selection, setSelection] = useState<Selection | null>(null);
  const [showRejected, setShowRejected] = useState(false);

  useEffect(() => {
    if (!focusId || !dossier) return;
    const finding = dossier.findings.find((item) => item.id === focusId);
    if (finding) {
      setSelection({ finding, index: 0 });
      setSeverity("all");
      setQuery("");
    }
  }, [focusId, dossier]);

  const visible = useMemo(() => {
    if (!dossier) return [];
    const needle = query.trim().toLowerCase();
    return [...dossier.findings]
      .filter((finding) => severity === "all" || finding.severity === severity)
      .filter((finding) => !needle || `${finding.id} ${finding.title} ${finding.category} ${finding.subcategory}`.toLowerCase().includes(needle))
      .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity));
  }, [dossier, severity, query]);

  if (!dossier) {
    return (
      <>
        <PageHeader title="Hallazgos" />
        <EmptyState title="Aún no hay hallazgos" action={<Button onClick={onGoHome}>Ir a Inicio</Button>}>Lanza una auditoría para ver los hallazgos con su evidencia.</EmptyState>
      </>
    );
  }
  if (dossier.findings.length === 0) {
    return (
      <>
        <PageHeader title="Hallazgos" />
        <EmptyState icon="✓" title="Sin hallazgos">Bob no reportó problemas con evidencia verificable.</EmptyState>
      </>
    );
  }

  const chip = (active: boolean) => `rounded-full border px-3 py-1 text-xs transition ${active ? "border-accent bg-accent/10 text-fg" : "border-line text-muted hover:border-accent/40"}`;

  const card = (finding: Finding, rejected: boolean) => {
    const open = selection?.finding.id === finding.id;
    return (
      <article key={finding.id} className={`rounded-xl border p-4 transition ${open ? "border-accent/60 bg-accent/5" : "border-line bg-surface"} ${rejected ? "border-dashed opacity-70" : ""}`}>
        <header className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={finding.severity} />
          <span className="font-mono text-xs text-muted">{finding.id}</span>
          <span className="text-xs text-muted">{finding.category} · {finding.subcategory}</span>
          <span className={`ml-auto rounded px-1.5 py-0.5 text-[11px] ${finding.observed_or_inferred === "observed" ? "bg-accent/10 text-accent" : "bg-warn/10 text-warn"}`}>
            {finding.observed_or_inferred === "observed" ? "Observado" : "Inferido"}
          </span>
        </header>
        <h3 className="mt-2 font-semibold leading-snug">{finding.title}</h3>
        <p className="mt-1.5 text-sm text-muted">{finding.explanation}</p>
        <p className="mt-2 rounded-lg bg-surface-2 px-3 py-2 text-sm"><span className="font-medium text-ok">Recomendación · </span>{finding.recommendation}</p>
        {rejected && <p className="mt-2 text-xs text-bad">Rechazado por el validador: su evidencia no coincide con el código.</p>}
        <ul className="mt-3 flex flex-wrap gap-2">
          {finding.evidence.map((evidence, index) => {
            const check = dossier.evidence_checks.find((item) => item.finding_id === finding.id && item.evidence_index === index);
            const active = open && selection?.index === index;
            const valid = check?.status === "valid";
            return (
              <li key={`${evidence.path}-${index}`}>
                <button type="button" onClick={() => setSelection({ finding, index })} aria-pressed={active}
                  className={`rounded-md border px-2 py-1 font-mono text-xs transition ${active ? "border-accent bg-accent text-accent-fg" : valid ? "border-ok/40 text-ok hover:bg-ok/10" : "border-bad/40 text-bad hover:bg-bad/10"}`}>
                  {valid ? "✓" : "✗"} {evidence.path}:{evidence.line_start}{evidence.line_end !== evidence.line_start ? `–${evidence.line_end}` : ""}
                </button>
              </li>
            );
          })}
        </ul>
      </article>
    );
  };

  return (
    <>
      <PageHeader title="Hallazgos" subtitle="Cada hallazgo abre el archivo y las líneas exactas que lo respaldan." right={<span className="text-sm text-muted">{visible.length} de {dossier.findings.length}</span>} />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => setSeverity("all")} className={chip(severity === "all")}>Todas</button>
        {SEVERITY_ORDER.map((level) => (
          <button key={level} type="button" onClick={() => setSeverity(level)} className={chip(severity === level)}>
            {SEVERITY_LABEL[level]} · {dossier.findings.filter((f) => f.severity === level).length}
          </button>
        ))}
        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar…" aria-label="Buscar hallazgos" className="ml-auto w-full rounded-lg border border-line bg-surface px-3 py-1.5 text-sm placeholder:text-muted sm:w-56" />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          {visible.length === 0 ? <EmptyState icon="⌕" title="Ningún hallazgo coincide">Prueba con otra severidad o borra la búsqueda.</EmptyState> : visible.map((finding) => card(finding, false))}
          {dossier.rejected_findings.length > 0 && (
            <div className="pt-2">
              <Button variant="ghost" onClick={() => setShowRejected((value) => !value)}>
                {showRejected ? "Ocultar" : "Ver"} {dossier.rejected_findings.length} rechazados por el validador
              </Button>
              {showRejected && <div className="mt-3 space-y-3">{dossier.rejected_findings.map((finding) => card(finding, true))}</div>}
            </div>
          )}
        </div>
        <div className="xl:sticky xl:top-20 xl:self-start">
          <Card className="p-4">
            <h2 className="mb-3 text-sm font-semibold">Visor de evidencia</h2>
            <EvidenceViewer jobId={jobId} token={token} selection={selection} dossier={dossier} />
          </Card>
        </div>
      </div>
    </>
  );
}
