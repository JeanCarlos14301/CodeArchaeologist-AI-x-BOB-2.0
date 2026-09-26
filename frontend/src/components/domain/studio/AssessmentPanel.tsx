import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "../../ui/Button";
import { Eyebrow } from "../../ui/Layout";
import { EvidenceRef } from "../EvidenceRef";
import { TechIcon } from "./TechIcon";
import type { Assessment, StackReport } from "../../../types";

const VERDICT = {
  recommended: { glyph: "✓", label: "Recomendado", tone: "text-verified", note: "Bob no encontró bloqueos. Aun así, valida cada paso con pruebas." },
  conditional: { glyph: "▲", label: "Con condiciones", tone: "text-warning", note: "Conviene solo si se resuelven los puntos de abajo primero." },
  not_recommended: { glyph: "✗", label: "No recomendado", tone: "text-danger", note: "Bob cree que el cambio no compensa en tu caso. Puedes seguir, pero con esta advertencia a la vista." },
} as const;

const AXIS: Record<string, string> = {
  security: "Seguridad", performance: "Rendimiento", cost: "Costo", maintainability: "Mantenibilidad",
  compatibility: "Compatibilidad", team: "Equipo", operations: "Operación",
};
const EFFECT = {
  improves: { glyph: "↑", label: "Mejora", tone: "text-verified" },
  worsens: { glyph: "↓", label: "Empeora", tone: "text-danger" },
  neutral: { glyph: "=", label: "Neutro", tone: "text-subtle" },
  depends: { glyph: "?", label: "Depende", tone: "text-warning" },
} as const;

interface Props {
  assessment: Assessment;
  stack: StackReport;
  planReady: boolean;
  busy: boolean;
  onPlan: () => void;
  onOpenFile: (path: string, line: number) => void;
}

/** Lo primero que se ve tras evaluar: veredicto y sacrificios, antes de cualquier plan (PRODUCT.md §17 y §46). */
export function AssessmentPanel({ assessment, stack, planReady, busy, onPlan, onOpenFile }: Props) {
  const [understood, setUnderstood] = useState(false);
  const verdict = VERDICT[assessment.verdict];
  const name = (id: string) => stack.technologies.find((t) => t.id === id) ?? Object.values(stack.targets).flat().find((t) => t.id === id);

  return (
    <div>
      <div className="grid gap-x-10 gap-y-4 @3xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div>
          <p className={`flex items-center gap-2 font-display text-title ${verdict.tone}`}><span aria-hidden>{verdict.glyph}</span>{verdict.label}</p>
          <p className="mt-2 text-body text-pretty text-fg">{assessment.summary}</p>
          <p className="mt-1 text-caption text-subtle">{verdict.note}</p>
        </div>
        <div>
          <Eyebrow>Lectura de tu negocio</Eyebrow>
          <p className="mt-1 text-body text-pretty text-fg-2">{assessment.business_reading}</p>
        </div>
      </div>

      {assessment.recommended.length > 0 && (
        <div className="mt-6">
          <Eyebrow>Destinos que propone Bob</Eyebrow>
          <ul className="mt-2 divide-y divide-line-subtle border-y border-line-subtle">
            {assessment.recommended.map((item) => {
              const from = name(item.from_id);
              const to = name(item.to_id);
              return (
                <li key={`${item.from_id}-${item.to_id}`} className="grid gap-x-6 gap-y-1 py-3 @2xl:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
                  <p className="flex items-center gap-2 text-body text-fg">
                    <TechIcon slug={from?.icon ?? null} name={from?.name ?? item.from_id} size={18} />{from?.name ?? item.from_id}
                    <span aria-hidden className="text-subtle">→</span>
                    <TechIcon slug={to?.icon ?? null} name={to?.name ?? item.to_id} size={18} />{to?.name ?? item.to_id}
                  </p>
                  <p className="text-caption text-pretty text-muted">{item.why}</p>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="mt-6">
        <Eyebrow>Qué se gana y qué se sacrifica</Eyebrow>
        <table className="mt-2 w-full border-t border-line-subtle text-left">
          <caption className="sr-only">Efecto de la migración por eje</caption>
          <thead className="sr-only"><tr><th scope="col">Eje</th><th scope="col">Efecto</th><th scope="col">Detalle</th></tr></thead>
          <tbody>
            {assessment.tradeoffs.map((tradeoff, index) => {
              const effect = EFFECT[tradeoff.effect];
              return (
                <tr key={`${tradeoff.axis}-${index}`} className="border-b border-line-subtle align-top">
                  <th scope="row" className="w-32 py-3 pr-4 text-left text-body font-normal text-fg">{AXIS[tradeoff.axis]}</th>
                  <td className={`w-28 py-3 pr-4 text-caption font-semibold ${effect.tone}`}><span aria-hidden className="mr-1.5">{effect.glyph}</span>{effect.label}</td>
                  <td className="py-3 text-body text-pretty text-fg-2">
                    {tradeoff.detail}
                    {tradeoff.refs.length > 0 && (
                      <span className="mt-2 flex flex-wrap gap-1.5">
                        {tradeoff.refs.map((ref) => (
                          <EvidenceRef key={`${ref.path}:${ref.line_start}`} path={ref.path} lineStart={ref.line_start} lineEnd={ref.line_end} verified={ref.verified}
                            onOpen={ref.verified ? () => onOpenFile(ref.path, ref.line_start) : undefined} />
                        ))}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {assessment.fixes_during_migration.length > 0 && (
        <div className="mt-6">
          <Eyebrow>Bob corregirá durante la migración</Eyebrow>
          <ul className="mt-2 space-y-1.5 text-body text-fg-2">
            {assessment.fixes_during_migration.map((item) => <li key={item} className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-verified">✓</span><span>{item}</span></li>)}
          </ul>
          <p className="mt-2 text-caption text-subtle">Los defectos del código actual no se portan al nuevo: cada paso los corrige al reescribir esa parte.</p>
        </div>
      )}

      {(assessment.blockers.length > 0 || assessment.questions.length > 0) && (
        <div className="mt-6 grid gap-x-10 gap-y-4 @3xl:grid-cols-2">
          {assessment.blockers.length > 0 && (
            <div>
              <Eyebrow>Bloqueos</Eyebrow>
              <ul className="mt-2 space-y-1.5 text-body text-fg-2">
                {assessment.blockers.map((item) => <li key={item} className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-danger">✗</span><span>{item}</span></li>)}
              </ul>
            </div>
          )}
          {assessment.questions.length > 0 && (
            <div>
              <Eyebrow>Bob necesita saber</Eyebrow>
              <ul className="mt-2 space-y-1.5 text-body text-fg-2">
                {assessment.questions.map((item) => <li key={item} className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-warning">?</span><span>{item}</span></li>)}
              </ul>
              <p className="mt-2 text-caption text-subtle">Añade la respuesta al contexto de arriba y evalúa de nuevo para afinarla.</p>
            </div>
          )}
        </div>
      )}

      {!planReady && (
        <div className="mt-7 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5">
          <label className="flex max-w-xl cursor-pointer items-start gap-3 text-body text-fg-2">
            <input type="checkbox" checked={understood} onChange={(event) => setUnderstood(event.target.checked)} className="mt-1 h-4 w-4 accent-[var(--ca-signal-orange)]" />
            <span>Entiendo lo que mejora y lo que empeora{assessment.verdict === "not_recommended" ? ", incluida la advertencia de que Bob no lo recomienda," : ""} y quiero seguir con esta decisión.</span>
          </label>
          <Button variant="primary" disabled={!understood || busy} onClick={onPlan} icon={<ArrowRight size={14} aria-hidden />}>
            {busy ? "Bob prepara el plan…" : "Generar plan detallado"}
          </Button>
        </div>
      )}
    </div>
  );
}
