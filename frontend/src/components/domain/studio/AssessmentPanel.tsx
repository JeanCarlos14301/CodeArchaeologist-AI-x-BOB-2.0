import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "../../ui/Button";
import { Eyebrow } from "../../ui/Layout";
import { EvidenceRef } from "../EvidenceRef";
import { TechIcon } from "./TechIcon";
import type { Assessment, StackReport } from "../../../types";
import { InlineText } from "../../ui/InlineText";

const VERDICT = {
  recommended: { glyph: "✓", label: "Recommended", tone: "text-verified", note: "Bob found no blockers. Even so, validate every step with tests." },
  conditional: { glyph: "▲", label: "Conditional", tone: "text-warning", note: "It pays off only if the points below are resolved first." },
  not_recommended: { glyph: "✗", label: "Not recommended", tone: "text-danger", note: "Bob thinks the change does not pay off in your case. You can go on, but with this warning in view." },
} as const;

const AXIS: Record<string, string> = {
  security: "Security", performance: "Performance", cost: "Cost", maintainability: "Maintainability",
  compatibility: "Compatibility", team: "Team", operations: "Operations",
};
const EFFECT = {
  improves: { glyph: "↑", label: "Improves", tone: "text-verified" },
  worsens: { glyph: "↓", label: "Worsens", tone: "text-danger" },
  neutral: { glyph: "=", label: "Neutral", tone: "text-subtle" },
  depends: { glyph: "?", label: "Depends", tone: "text-warning" },
} as const;

interface Props {
  assessment: Assessment;
  stack: StackReport;
  planReady: boolean;
  busy: boolean;
  onPlan: () => void;
  onOpenFile: (path: string, line: number) => void;
  /** Answers in progress, per Bob question. */
  answers: Record<string, string>;
  onAnswer: (question: string, answer: string) => void;
  /** Questions the person already answered in previous rounds. */
  history: { question: string; answer: string }[];
  onReassess: () => void;
  reassessBusy: boolean;
  hasToken: boolean;
}

/** The first thing shown after assessing: verdict and trade-offs, before any plan (PRODUCT.md §17 and §46). */
const QUICK = ["Yes", "No", "I don't know"];

export function AssessmentPanel({ assessment, stack, planReady, busy, onPlan, onOpenFile, answers, onAnswer, history, onReassess, reassessBusy, hasToken }: Props) {
  const [understood, setUnderstood] = useState(false);
  const verdict = VERDICT[assessment.verdict];
  const answered = Object.values(answers).some((value) => value.trim().length > 0);
  const name = (id: string) => stack.technologies.find((t) => t.id === id) ?? Object.values(stack.targets).flat().find((t) => t.id === id);

  return (
    <div>
      <div className="grid grid-cols-1 gap-x-10 gap-y-4 @3xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div>
          <p className={`flex items-center gap-2 font-display text-title ${verdict.tone}`}><span aria-hidden>{verdict.glyph}</span>{verdict.label}</p>
          <p className="mt-2 text-body text-pretty text-fg"><InlineText text={assessment.summary} /></p>
          <p className="mt-1 text-caption text-subtle">{verdict.note}</p>
        </div>
        <div>
          <Eyebrow>Reading of your business</Eyebrow>
          <p className="mt-1 text-body text-pretty text-fg-2"><InlineText text={assessment.business_reading} /></p>
        </div>
      </div>

      {assessment.recommended.length > 0 && (
        <div className="mt-6">
          <Eyebrow>Targets Bob proposes</Eyebrow>
          <ul className="mt-2 divide-y divide-line-subtle border-y border-line-subtle">
            {assessment.recommended.map((item) => {
              const from = name(item.from_id);
              const to = name(item.to_id);
              return (
                <li key={`${item.from_id}-${item.to_id}`} className="grid grid-cols-1 gap-x-6 gap-y-1 py-3 @2xl:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
                  <p className="flex items-center gap-2 text-body text-fg">
                    <TechIcon slug={from?.icon ?? null} name={from?.name ?? item.from_id} size={18} />{from?.name ?? item.from_id}
                    <span aria-hidden className="text-subtle">→</span>
                    <TechIcon slug={to?.icon ?? null} name={to?.name ?? item.to_id} size={18} />{to?.name ?? item.to_id}
                  </p>
                  <p className="text-caption text-pretty text-muted"><InlineText text={item.why} /></p>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="mt-6">
        <Eyebrow>What is gained and what is traded away</Eyebrow>
        <table className="mt-2 w-full border-t border-line-subtle text-left">
          <caption className="sr-only">Effect of the migration per axis</caption>
          <thead className="sr-only"><tr><th scope="col">Axis</th><th scope="col">Effect</th><th scope="col">Detail</th></tr></thead>
          <tbody>
            {assessment.tradeoffs.map((tradeoff, index) => {
              const effect = EFFECT[tradeoff.effect];
              return (
                <tr key={`${tradeoff.axis}-${index}`} className="border-b border-line-subtle align-top">
                  <th scope="row" className="w-32 py-3 pr-4 text-left text-body font-normal text-fg">{AXIS[tradeoff.axis]}</th>
                  <td className={`w-28 py-3 pr-4 text-caption font-semibold ${effect.tone}`}><span aria-hidden className="mr-1.5">{effect.glyph}</span>{effect.label}</td>
                  <td className="py-3 text-body text-pretty text-fg-2">
                    <InlineText text={tradeoff.detail} />
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
          <Eyebrow>Bob will fix during the migration</Eyebrow>
          <ul className="mt-2 space-y-1.5 text-body text-fg-2">
            {assessment.fixes_during_migration.map((item) => <li key={item} className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-verified">✓</span><span>{item}</span></li>)}
          </ul>
          <p className="mt-2 text-caption text-subtle">Defects in the current code are not carried over: each step fixes them while rewriting that part.</p>
        </div>
      )}

      {assessment.blockers.length > 0 && (
        <div className="mt-6">
          <Eyebrow>Blockers</Eyebrow>
          <ul className="mt-2 space-y-1.5 text-body text-fg-2">
            {assessment.blockers.map((item) => <li key={item} className="grid grid-cols-[1.25rem_1fr]"><span aria-hidden className="text-danger">✗</span><span><InlineText text={item} /></span></li>)}
          </ul>
        </div>
      )}

      {assessment.questions.length > 0 && (
        <div className="mt-6 border-t border-line pt-5">
          <Eyebrow>Bob needs to know</Eyebrow>
          <p className="mt-1 max-w-2xl text-caption text-pretty text-muted">Answer right here and Bob assesses again with your answers. You can leave blank what you do not know.</p>
          <ul className="mt-4 space-y-5">
            {assessment.questions.map((question, index) => {
              const id = `answer-${index}`;
              const value = answers[question] ?? "";
              return (
                <li key={question}>
                  <label htmlFor={id} className="grid grid-cols-[1.25rem_1fr] text-body text-fg"><span aria-hidden className="text-warning">?</span><span><InlineText text={question} /></span></label>
                  <div className="mt-2 ml-5 flex flex-wrap items-start gap-2">
                    <div role="group" aria-label="Quick answers" className="flex gap-1.5">
                      {QUICK.map((quick) => (
                        <button key={quick} type="button" aria-pressed={value === quick} onClick={() => onAnswer(question, value === quick ? "" : quick)}
                          className={`inline-flex h-7 items-center rounded-pill border px-3 text-caption transition-[border-color,background-color] duration-150 ease-out ${value === quick ? "border-line-strong bg-raised text-fg" : "border-line text-muted hover:border-line-strong hover:text-fg"}`}>{quick}</button>
                      ))}
                    </div>
                    <textarea id={id} rows={2} maxLength={800} value={value} onChange={(event) => onAnswer(question, event.target.value)} placeholder="Write your answer or add nuance…"
                      className="min-w-56 flex-1 resize-y rounded-inner border border-line bg-control px-3 py-1.5 text-caption text-fg placeholder:text-subtle focus:border-focus focus:outline-none" />
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button variant="secondary" disabled={!answered || reassessBusy || !hasToken} onClick={onReassess}>
              {reassessBusy ? "Bob is assessing again…" : "Send answers and assess again"}
            </Button>
            {planReady && <span className="text-caption text-warning">Assessing again discards the current plan and implementation.</span>}
            {!hasToken && <span className="text-caption text-subtle">Enter the token in «Migration targets» to be able to answer.</span>}
          </div>
        </div>
      )}

      {history.length > 0 && (
        <details className="mt-5 text-caption text-muted">
          <summary className="cursor-pointer text-fg-2">You already answered {history.length} {history.length === 1 ? "question" : "questions"} from Bob</summary>
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
            <input type="checkbox" checked={understood} onChange={(event) => setUnderstood(event.target.checked)} className="mt-1 h-4 w-4 accent-accent" />
            <span>I understand what improves and what gets worse{assessment.verdict === "not_recommended" ? ", including the warning that Bob does not recommend it," : ""} and I want to go on with this decision.</span>
          </label>
          <Button variant="primary" disabled={!understood || busy} onClick={onPlan} icon={<ArrowRight size={14} aria-hidden />}>
            {busy ? "Bob is preparing the plan…" : "Generate a detailed plan"}
          </Button>
        </div>
      )}
    </div>
  );
}
