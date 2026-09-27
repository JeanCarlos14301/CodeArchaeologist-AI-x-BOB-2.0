import { formatDecimal } from "../../lib/format";
import type { Dossier } from "../../types";

type Pert = NonNullable<Dossier["first_cut_pert"]>;

/** PERT range as a ruler: optimistic · most likely · expected · pessimistic (all computed by code). */
export function PertRange({ pert }: { pert: Pert }) {
  const min = pert.optimistic_days;
  const span = Math.max(pert.pessimistic_days - min, 0.0001);
  const at = (value: number) => `${((value - min) / span) * 100}%`;
  const ticks = [
    { label: "Optimistic", value: pert.optimistic_days, align: "left" as const },
    { label: "Most likely", value: pert.most_likely_days, align: "center" as const },
    { label: "Pessimistic", value: pert.pessimistic_days, align: "right" as const },
  ];
  return (
    <figure aria-label={`PERT estimate: expected ${formatDecimal(pert.expected_days)} days, between ${formatDecimal(min)} and ${formatDecimal(pert.pessimistic_days)}`}>
      <div className="flex items-baseline gap-2">
        <span className="font-display text-heading text-fg tabular-nums">{formatDecimal(pert.expected_days)}</span>
        <span className="text-body text-muted">expected days</span>
        <span className="ml-auto font-mono text-caption text-subtle">σ² = {formatDecimal(pert.variance)}</span>
      </div>
      <div className="relative mt-5 mb-9 h-px bg-line-strong">
        <span aria-hidden className="absolute -top-1 h-2.5 w-px bg-fg" style={{ left: at(pert.expected_days) }} />
        <span aria-hidden className="absolute -top-5 -translate-x-1/2 font-mono text-micro text-fg" style={{ left: at(pert.expected_days) }}>E</span>
        {ticks.map((tick) => (
          <span key={tick.label} className="absolute top-0" style={{ left: at(tick.value) }}>
            <span aria-hidden className="absolute -top-1 h-2 w-px bg-subtle" />
            <span className={`absolute top-2 whitespace-nowrap text-caption text-subtle ${tick.align === "center" ? "-translate-x-1/2" : tick.align === "right" ? "-translate-x-full" : ""}`}>
              {tick.label} <span className="font-mono text-fg-2">{formatDecimal(tick.value)} d</span>
            </span>
          </span>
        ))}
      </div>
      <figcaption className="font-mono text-caption text-subtle">{pert.formula}</figcaption>
    </figure>
  );
}
