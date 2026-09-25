import type { Evidence, EvidenceCheck, Finding, Severity } from "../types";

const SEVERITY_STYLE: Record<Severity, string> = {
  critical: "bg-rose-600 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-amber-200 text-amber-900",
  low: "bg-stone-200 text-stone-700",
};
const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];

interface Props {
  findings: Finding[];
  rejected: Finding[];
  checks: EvidenceCheck[];
  selected: { findingId: string; evidenceIndex: number } | null;
  onSelect: (finding: Finding, evidence: Evidence, index: number) => void;
}

function FindingCard({
  finding,
  rejected,
  checks,
  selected,
  onSelect,
}: { finding: Finding; rejected: boolean } & Omit<Props, "findings" | "rejected">) {
  return (
    <article className={`rounded-md border bg-white p-3 ${rejected ? "border-dashed border-stone-300 opacity-70" : "border-stone-200"}`}>
      <header className="mb-1 flex flex-wrap items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase ${SEVERITY_STYLE[finding.severity]}`}>
          {finding.severity}
        </span>
        <span className="font-mono text-xs text-stone-500">{finding.id}</span>
        <span className="text-xs text-stone-500">
          {finding.category} · {finding.observed_or_inferred === "observed" ? "observado" : "inferido"}
        </span>
        {rejected && <span className="text-xs font-medium text-rose-700">rechazado por el validador</span>}
      </header>
      <h3 className="text-sm font-semibold leading-snug">{finding.title}</h3>
      <p className="mt-1 text-sm text-stone-700">{finding.explanation}</p>
      <p className="mt-1 text-sm text-stone-600">
        <span className="font-medium">Recomendación:</span> {finding.recommendation}
      </p>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {finding.evidence.map((evidence, index) => {
          const check = checks.find((item) => item.finding_id === finding.id && item.evidence_index === index);
          const isSelected = selected?.findingId === finding.id && selected.evidenceIndex === index;
          const valid = check?.status === "valid";
          return (
            <li key={`${evidence.path}-${index}`}>
              <button
                type="button"
                title={check?.reason}
                onClick={() => onSelect(finding, evidence, index)}
                className={`rounded border px-1.5 py-0.5 font-mono text-xs ${
                  isSelected ? "border-stone-900 bg-stone-900 text-white" : valid ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-rose-300 bg-rose-50 text-rose-900"
                }`}
              >
                {valid ? "✓" : "✗"} {evidence.path}:{evidence.line_start}
                {evidence.line_end !== evidence.line_start ? `–${evidence.line_end}` : ""}
              </button>
            </li>
          );
        })}
      </ul>
    </article>
  );
}

export function FindingsList({ findings, rejected, checks, selected, onSelect }: Props) {
  const sorted = [...findings].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );
  return (
    <div className="space-y-2">
      {sorted.map((finding) => (
        <FindingCard key={finding.id} finding={finding} rejected={false} checks={checks} selected={selected} onSelect={onSelect} />
      ))}
      {rejected.length > 0 && (
        <>
          <h3 className="pt-2 text-xs font-semibold uppercase tracking-wide text-stone-500">
            Rechazados ({rejected.length}): su evidencia no coincide con el código
          </h3>
          {rejected.map((finding) => (
            <FindingCard key={finding.id} finding={finding} rejected checks={checks} selected={selected} onSelect={onSelect} />
          ))}
        </>
      )}
    </div>
  );
}
