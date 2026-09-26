import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { FindingInspector } from "../components/domain/FindingInspector";
import { RiskRow } from "../components/domain/RiskRow";
import { Button } from "../components/ui/Button";
import { ScreenHeader, Segmented } from "../components/ui/Layout";
import { EmptyState } from "../components/ui/States";
import { SEVERITY, SEVERITY_ORDER, bySeverity, categoryLabel, countBySeverity } from "../lib/severity";
import { useResource, useWorkspace } from "../lib/workspace";
import type { Dossier, Severity } from "../types";
import { JobGate } from "./JobGate";

export function RisksView() {
  return <JobGate>{(dossier) => <Risks dossier={dossier} />}</JobGate>;
}

function Risks({ dossier }: { dossier: Dossier }) {
  const { route, go } = useWorkspace();
  const graph = useResource("graph").data;
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [category, setCategory] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [showRejected, setShowRejected] = useState(false);
  const counts = countBySeverity(dossier.findings);
  const categories = [...new Set(dossier.findings.map((f) => f.category))].sort();

  const impacted = (id: string) => {
    if (!graph) return null;
    return graph.blast_radius.find((b) => b.finding_id === id)?.impacted_nodes.length ?? 0;
  };
  const score = (id: string) => dossier.risk_matrix.find((r) => r.finding_id === id)?.score ?? null;

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return [...dossier.findings]
      .filter((f) => severity === "all" || f.severity === severity)
      .filter((f) => category === "all" || f.category === category)
      .filter((f) => !needle || `${f.id} ${f.title} ${f.subcategory} ${f.evidence.map((e) => e.path).join(" ")}`.toLowerCase().includes(needle))
      .sort(bySeverity);
  }, [dossier.findings, severity, category, query]);

  const all = [...dossier.findings, ...dossier.rejected_findings];
  const selected = all.find((f) => f.id === route.finding) ?? visible[0] ?? null;
  const selectedRejected = !!selected && dossier.rejected_findings.some((f) => f.id === selected.id);
  const groups = SEVERITY_ORDER.map((level) => ({ level, items: visible.filter((f) => f.severity === level) })).filter((g) => g.items.length);

  const select = (id: string) => go("risks", { finding: id });

  return (
    <div className="flex flex-col @3xl:h-full @3xl:min-h-0">
      <div className="px-6 pt-6 @3xl:px-10">
        <ScreenHeader
          eyebrow="Riesgos · ¿Qué podría complicar la modernización?"
          title={`${dossier.findings.length} hallazgos con evidencia`}
          description="Cada hallazgo apunta a un archivo y unas líneas que el validador comprobó. Selecciona uno para ver su evidencia, el código afectado y la acción recomendada."
        />
        <div className="flex flex-wrap items-center gap-3 py-4">
          <Segmented<Severity | "all">
            label="Filtrar por severidad"
            value={severity}
            onChange={setSeverity}
            options={[
              { value: "all", label: <>Todas <span className="font-mono text-subtle">{dossier.findings.length}</span></> },
              ...SEVERITY_ORDER.filter((level) => counts[level] > 0).map((level) => ({
                value: level,
                label: <><span aria-hidden className={SEVERITY[level].text}>{SEVERITY[level].glyph}</span>{SEVERITY[level].label} <span className="font-mono text-subtle">{counts[level]}</span></>,
              })),
            ]}
          />
          <label className="sr-only" htmlFor="risk-category">Categoría</label>
          <select id="risk-category" value={category} onChange={(event) => setCategory(event.target.value)}
            className="h-8 rounded-pill border border-line bg-control px-3 text-caption text-fg-2 focus:border-focus focus:outline-none">
            <option value="all">Todas las categorías</option>
            {categories.map((c) => <option key={c} value={c}>{categoryLabel(c)}</option>)}
          </select>
          <div className="relative ml-auto w-full sm:w-64">
            <Search size={14} aria-hidden className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-subtle" />
            <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por título, id o archivo" aria-label="Buscar hallazgos"
              className="h-8 w-full rounded-pill border border-line bg-control pr-3 pl-8 text-caption text-fg placeholder:text-subtle focus:border-focus focus:outline-none" />
          </div>
        </div>
      </div>

      <div className="grid border-t border-line @3xl:min-h-0 @3xl:flex-1 @3xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="@3xl:min-h-0 @3xl:overflow-y-auto @3xl:border-r @3xl:border-line">
          {groups.length === 0 ? (
            <div className="p-6">
              <EmptyState title="Ningún hallazgo coincide con los filtros." action={<Button size="sm" onClick={() => { setSeverity("all"); setCategory("all"); setQuery(""); }}>Quitar filtros</Button>} />
            </div>
          ) : (
            groups.map((group) => (
              <section key={group.level} aria-label={`${SEVERITY[group.level].label}: ${group.items.length}`}>
                <h2 className={`sticky top-0 z-10 flex items-center gap-2 border-b border-line bg-canvas px-4 py-2 text-micro font-semibold tracking-eyebrow uppercase ${SEVERITY[group.level].text}`}>
                  <span aria-hidden>{SEVERITY[group.level].glyph}</span>{SEVERITY[group.level].label}
                  <span className="font-mono text-subtle">{group.items.length}</span>
                </h2>
                <ul>
                  {group.items.map((finding) => (
                    <RiskRow key={finding.id} finding={finding} impacted={impacted(finding.id)} score={score(finding.id)} selected={selected?.id === finding.id} onSelect={() => select(finding.id)} />
                  ))}
                </ul>
              </section>
            ))
          )}
          {dossier.rejected_findings.length > 0 && (
            <div className="border-t border-line p-4">
              <Button size="sm" variant="ghost" onClick={() => setShowRejected((v) => !v)} aria-expanded={showRejected}>
                {showRejected ? "Ocultar" : "Mostrar"} {dossier.rejected_findings.length} descartados por el validador
              </Button>
              {showRejected && (
                <ul className="mt-2">
                  {dossier.rejected_findings.map((finding) => (
                    <RiskRow key={finding.id} finding={finding} impacted={null} score={null} rejected selected={selected?.id === finding.id} onSelect={() => select(finding.id)} />
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-line px-6 py-6 @3xl:min-h-0 @3xl:overflow-y-auto @3xl:border-t-0">
          {selected ? (
            <FindingInspector key={selected.id} finding={selected} dossier={dossier} graph={graph} rejected={selectedRejected} />
          ) : (
            <EmptyState title="Selecciona un hallazgo">Verás su evidencia, el código afectado y la acción recomendada.</EmptyState>
          )}
        </div>
      </div>
    </div>
  );
}
