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
  /** Respuestas en curso, por pregunta de Bob. */
  answers: Record<string, string>;
  onAnswer: (question: string, answer: string) => void;
  /** Preguntas que la persona ya contestó en rondas anteriores. */
  history: { question: string; answer: string }[];
  onReassess: () => void;
  reassessBusy: boolean;
  hasToken: boolean;
}

/** Lo primero que se ve tras evaluar: veredicto y sacrificios, antes de cualquier plan (PRODUCT.md §17 y §46). */
const QUICK = ["Sí", "No", "No lo sé"];

export function AssessmentPanel({ assessment, stack, planReady, busy, onPlan, onOpenFile, answers, onAnswer, history, onReassess, reassessBusy, hasToken }: Props) {
  const [understood, setUnderstood] = useState(false);
  const verdict = VERDICT[assessment.verdict];
  const answered = Object.values(answers).some((value) => value.trim().length > 0);
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

      {assessment.blockers.length > 0 && (
        <div className="mt-6">
          <Eyebrow>Bloqueos</Eyebrow>
          <ul className="mt-2 space-y-1.5 text-body text-fg-2">
            {assessment.blockers.map((item) => <li key={item} className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-danger">✗</span><span>{item}</span></li>)}
          </ul>
        </div>
      )}

      {assessment.questions.length > 0 && (
        <div className="mt-6 border-t border-line pt-5">
          <Eyebrow>Bob necesita saber</Eyebrow>
          <p className="mt-1 max-w-2xl text-caption text-pretty text-muted">Respóndele aquí mismo y Bob vuelve a evaluar con tus respuestas. Puedes dejar en blanco lo que no sepas.</p>
          <ul className="mt-4 space-y-5">
            {assessment.questions.map((question, index) => {
              const id = `answer-${index}`;
              const value = answers[question] ?? "";
              return (
                <li key={question}>
                  <label htmlFor={id} className="grid grid-cols-[1.25rem_1fr] text-body text-fg"><span aria-hidden className="text-warning">?</span><span>{question}</span></label>
                  <div className="mt-2 ml-5 flex flex-wrap items-start gap-2">
                    <div role="group" aria-label="Respuestas rápidas" className="flex gap-1.5">
                      {QUICK.map((quick) => (
                        <button key={quick} type="button" aria-pressed={value === quick} onClick={() => onAnswer(question, value === quick ? "" : quick)}
                          className={`inline-flex h-7 items-center rounded-pill border px-3 text-caption transition-[border-color,background-color] duration-150 ease-out ${value === quick ? "border-line-strong bg-raised text-fg" : "border-line text-muted hover:border-line-strong hover:text-fg"}`}>{quick}</button>
                      ))}
                    </div>
                    <textarea id={id} rows={2} maxLength={800} value={value} onChange={(event) => onAnswer(question, event.target.value)} placeholder="Escribe tu respuesta o matiza…"
                      className="min-w-56 flex-1 resize-y rounded-inner border border-line bg-control px-3 py-1.5 text-caption text-fg placeholder:text-subtle focus:border-focus focus:outline-none" />
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button variant="secondary" disabled={!answered || reassessBusy || !hasToken} onClick={onReassess}>
              {reassessBusy ? "Bob está evaluando de nuevo…" : "Enviar respuestas y evaluar de nuevo"}
            </Button>
            {planReady && <span className="text-caption text-warning">Evaluar de nuevo descarta el plan y la implementación actuales.</span>}
            {!hasToken && <span className="text-caption text-subtle">Introduce el token en «Destinos de la migración» para poder responder.</span>}
          </div>
        </div>
      )}

      {history.length > 0 && (
        <details className="mt-5 text-caption text-muted">
          <summary className="cursor-pointer text-fg-2">Ya le respondiste a Bob {history.length} {history.length === 1 ? "pregunta" : "preguntas"}</summary>
          <ul className="mt-2 space-y-2">
            {history.map((item) => (
              <li key={item.question} className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-verified">✓</span><span><span className="text-fg-2">{item.question}</span><span className="block text-fg">→ {item.answer}</span></span></li>
            ))}
          </ul>
        </details>
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
