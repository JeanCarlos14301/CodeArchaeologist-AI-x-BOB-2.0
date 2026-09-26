import { categoryLabel, SEVERITY } from "../../lib/severity";
import { lineRange, plural } from "../../lib/format";
import type { Finding } from "../../types";

interface Props {
  finding: Finding;
  impacted: number | null;
  score: number | null;
  selected: boolean;
  rejected?: boolean;
  onSelect: () => void;
}

/** Un hallazgo como fila densa: categoría · severidad · título · evidencia · confianza (PRODUCT.md §43). */
export function RiskRow({ finding, impacted, score, selected, rejected = false, onSelect }: Props) {
  const severity = SEVERITY[finding.severity];
  const evidence = finding.evidence[0];
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-current={selected ? "true" : undefined}
        className={`group relative grid w-full grid-cols-[1fr_auto] gap-x-4 gap-y-1 border-b border-line-subtle px-4 py-3.5 text-left transition-[background-color] duration-150 ease-out hover:bg-raised ${selected ? "bg-raised" : ""} ${rejected ? "opacity-60" : ""}`}
      >
        <span aria-hidden className={`absolute inset-y-2 left-0 w-0.5 rounded-pill ${selected ? "bg-accent-hover" : "bg-transparent"}`} />
        <span className="text-micro tracking-eyebrow text-subtle uppercase">
          {categoryLabel(finding.category)} <span className="text-decor">/</span> {finding.subcategory}
        </span>
        <span className={`text-micro font-semibold tracking-eyebrow uppercase ${severity.text}`}>
          <span aria-hidden className="mr-1.5">{severity.glyph}</span>{severity.label}
        </span>
        <span className="col-span-2 text-body text-pretty text-fg group-hover:text-fg">{finding.title}</span>
        <span className="col-span-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-subtle">
          {evidence && <span className="font-mono text-fg-2">{evidence.path}:{lineRange(evidence.line_start, evidence.line_end)}</span>}
          <span>{finding.observed_or_inferred === "observed" ? "Observado en el código" : "Inferido"}</span>
          {impacted !== null && <span>{impacted === 0 ? "Sin llamadores afectados" : plural(impacted, "llamador afectado", "llamadores afectados")}</span>}
          {score !== null && <span className="font-mono">riesgo {score}</span>}
          {rejected && <span className="text-danger">✗ evidencia no coincide con el código</span>}
          <span className="font-mono text-subtle">{finding.id}</span>
        </span>
      </button>
    </li>
  );
}
