import type { Dossier, Finding } from "../../types";
import { SEVERITY } from "../../lib/severity";

interface Props {
  options: NonNullable<Dossier["migration_options"]>;
  findings: Finding[];
  onOpenFinding: (id: string) => void;
}

/**
 * Opciones propuestas por Bob (migration-architect). Las valida el código: sus hallazgos existen en el ranking
 * y no traen cifras. Los días, el riesgo y el radio no salen de aquí: se calculan aparte (PERT y ranking).
 */
export function MigrationOptions({ options, findings, onOpenFinding }: Props) {
  const byId = new Map(findings.map((finding) => [finding.id, finding]));
  return (
    <ol className="divide-y divide-line-subtle border-y border-line-subtle">
      {options.map((option) => (
        <li key={option.id} className={`grid gap-x-8 gap-y-3 px-1 py-4 @3xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] ${option.recommended ? "bg-raised" : ""}`}>
          <div>
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-micro tracking-eyebrow text-subtle uppercase">
              <span className="font-mono">{option.id}</span>
              <span className="text-decor" aria-hidden>/</span>
              <span>{option.pattern}</span>
              {option.recommended && <span className="font-semibold text-verified"><span aria-hidden>✓ </span>Recomendada</span>}
            </p>
            <h3 className="mt-1 font-display text-title text-balance text-fg">{option.name}</h3>
            <p className="mt-2 text-micro tracking-eyebrow text-subtle uppercase">Ataca</p>
            <ul className="mt-1 flex flex-wrap gap-1.5">
              {option.finding_ids.map((id) => {
                const finding = byId.get(id);
                const info = finding ? SEVERITY[finding.severity] : null;
                return (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => onOpenFinding(id)}
                      title={finding?.title}
                      className="inline-flex h-5.5 items-center gap-1.5 rounded-pill border border-line px-2.5 font-mono text-caption text-fg-2 transition-[background-color] duration-150 ease-out hover:bg-raised"
                    >
                      {info && <span aria-hidden className={info.text}>{info.glyph}</span>}
                      {id}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
          <div className="grid gap-4 @xl:grid-cols-2">
            <ul className="space-y-1.5 text-caption text-fg-2">
              {option.pros.map((pro) => <li key={pro} className="grid grid-cols-[1rem_1fr] gap-1"><span aria-hidden className="text-verified">+</span><span><span className="sr-only">Ventaja: </span>{pro}</span></li>)}
            </ul>
            <ul className="space-y-1.5 text-caption text-fg-2">
              {option.cons.map((con) => <li key={con} className="grid grid-cols-[1rem_1fr] gap-1"><span aria-hidden className="text-danger">−</span><span><span className="sr-only">Riesgo: </span>{con}</span></li>)}
            </ul>
          </div>
        </li>
      ))}
    </ol>
  );
}
