import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";
import { formatCost, formatSeconds } from "../../lib/format";
import { useWorkspace, type AskEntry } from "../../lib/workspace";
import type { AskContext, AskStep, Claim } from "../../types";
import { InlineText } from "../ui/InlineText";
import { Eyebrow } from "../ui/Layout";
import { EvidenceRef } from "./EvidenceRef";
import { BOB_GLYPH, BobWork, bobCounters, type BobWorkEvent } from "./BobWork";

const BOOKKEEPING = new Set(["bob.turn", "bob.result", "bob.start"]);
/** Lo que Bob HACE (lecturas, búsquedas, skills, razonamiento); sin sus turnos ni el cierre de sesión. */
export const visibleSteps = (steps: AskStep[]): AskStep[] => steps.filter((step) => !BOOKKEEPING.has(step.kind));

const asWork = (steps: AskStep[], startedAt: number): BobWorkEvent[] =>
  visibleSteps(steps).map((step) => ({ t: startedAt + step.t, kind: step.kind, message: step.message, detail: step.detail, data: step.data }));

/** Cómo llegó Bob a la respuesta: los pasos reales, plegados para no ocupar el chat. */
function HowBobGotThere({ steps: all, startedAt }: { steps: AskStep[]; startedAt: number }) {
  const steps = visibleSteps(all);
  if (steps.length === 0) return null;
  const counters = bobCounters(asWork(steps, startedAt));
  return (
    <details className="group rounded-inner border border-line-subtle px-3 py-2">
      <summary className="cursor-pointer list-none text-caption text-muted marker:hidden hover:text-fg">
        <span aria-hidden className="mr-1.5 inline-block transition-transform duration-150 group-open:rotate-90">›</span>
        Cómo llegó Bob a esta respuesta · {steps.length} {steps.length === 1 ? "paso" : "pasos"}
        {counters.length > 0 && <span className="text-subtle"> · {counters.map((c) => `${c.value} ${c.label}`).join(" · ")}</span>}
      </summary>
      <ol className="mt-2 max-h-56 space-y-1 overflow-y-auto overscroll-contain border-l border-line pl-3">
        {steps.map((step) => {
          const style = BOB_GLYPH[step.kind] ?? BOB_GLYPH.info;
          return (
            <li key={step.seq} className="grid grid-cols-[2.25rem_1.25rem_minmax(0,1fr)] text-caption">
              <span className="font-mono text-micro text-subtle tabular-nums">{Math.round(step.t)} s</span>
              <span aria-hidden className={style.tone}>{style.glyph}</span>
              <span className="min-w-0 text-fg-2">{step.message}</span>
            </li>
          );
        })}
      </ol>
    </details>
  );
}

const SECTIONS: { key: "facts" | "inferences" | "recommendations"; label: string; tone: string }[] = [
  { key: "facts", label: "Hechos detectados", tone: "text-verified" },
  { key: "inferences", label: "Inferencias", tone: "text-warning" },
  { key: "recommendations", label: "Recomendaciones", tone: "text-fg" },
];

/** Respuesta de Bob con hechos, inferencias, recomendaciones y desconocidos (PRODUCT.md §20). */
export function AskAnswerView({ entry }: { entry: AskEntry }) {
  const { go } = useWorkspace();
  if (entry.status === "pending") {
    return <BobWork compact title="Bob está trabajando en tu pregunta" events={asWork(entry.progress, entry.startedAt)} since={entry.startedAt} />;
  }
  if (entry.status === "error" || !entry.answer) {
    return (
      <p role="alert" className="text-caption text-danger">
        <span aria-hidden>✗ </span>{entry.error ?? "Bob no respondió."}
      </p>
    );
  }
  const answer = entry.answer;
  const openRef = (path: string, line: number) => go("repository", { file: path, line });
  const claims = (list: Claim[]) =>
    list.map((claim, i) => (
      <li key={i} className="text-body text-pretty text-fg-2">
        <InlineText text={claim.text} />
        {claim.refs.length > 0 && (
          <span className="mt-1 flex flex-wrap gap-1.5">
            {claim.refs.map((ref, j) => (
              <EvidenceRef key={j} path={ref.path} lineStart={ref.line_start} lineEnd={ref.line_end} verified={ref.verified}
                reason={ref.verified ? "El archivo y las líneas existen en el repositorio" : "La cita no existe en el repositorio analizado"}
                onOpen={ref.verified ? () => openRef(ref.path, ref.line_start) : undefined} />
            ))}
          </span>
        )}
      </li>
    ));

  return (
    <div className="space-y-3" aria-live="polite">
      <p className="text-body text-pretty text-fg"><InlineText text={answer.summary} /></p>
      {!answer.structured && <p className="text-caption text-warning">Bob respondió en texto libre: no se pudieron separar hechos de inferencias ni verificar citas.</p>}
      {SECTIONS.map((section) => answer[section.key].length > 0 && (
        <section key={section.key}>
          <Eyebrow className={section.tone}>{section.label}</Eyebrow>
          <ul className="mt-1.5 space-y-2">{claims(answer[section.key])}</ul>
        </section>
      ))}
      {answer.unknowns.length > 0 && (
        <section>
          <Eyebrow>Desconocido con el código disponible</Eyebrow>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-caption text-muted">
            {answer.unknowns.map((item, i) => <li key={i}><InlineText text={item} /></li>)}
          </ul>
        </section>
      )}
      <HowBobGotThere steps={entry.progress} startedAt={entry.startedAt} />
      <p className="font-mono text-micro text-subtle">IBM Bob · modo ask · {formatCost(answer.bob_cost)} · {formatSeconds(answer.bob_duration_ms)}</p>
    </div>
  );
}

const MIN_QUESTION = 3;
const MAX_QUESTION = 800;

/** Composer de preguntas: shell carbon + orbe naranja (referencia "Hero Prompt Composer"). */
export function AskComposer({ context, disabledReason }: { context: AskContext; disabledReason: string | null }) {
  const { ask, askHistory, token, setToken, composerSeed, clearComposerSeed } = useWorkspace();
  const [text, setText] = useState("");
  const [draftToken, setDraftToken] = useState("");
  const area = useRef<HTMLTextAreaElement>(null);
  const pending = askHistory.some((entry) => entry.status === "pending");

  useEffect(() => {
    if (!composerSeed) return;
    setText(composerSeed.text);
    area.current?.focus();
    // La semilla se consume: si el panel se vuelve a montar tras la respuesta, no reaparece la pregunta anterior.
    clearComposerSeed();
  }, [composerSeed, clearComposerSeed]);

  const question = text.trim();
  const blocked = disabledReason ?? (pending ? "Bob está respondiendo la pregunta anterior." : null);
  const canSend = !blocked && !!token && question.length >= MIN_QUESTION;

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!canSend) return;
    void ask(question, context);
    setText("");
  };

  const onKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={submit} className="space-y-2">
      {!token && !disabledReason && (
        <div className="rounded-inner border border-line px-3 py-2.5">
          <label className="block text-caption text-muted" htmlFor="ask-token">Token de acceso · cada pregunta consume bobcoins</label>
          <div className="mt-1.5 flex gap-2">
            <input id="ask-token" type="password" autoComplete="off" value={draftToken} onChange={(event) => setDraftToken(event.target.value)}
              className="h-7 min-w-0 flex-1 rounded-pill border border-line bg-control px-3 font-mono text-caption text-fg placeholder:text-subtle focus:border-focus focus:outline-none" placeholder="X-Live-Token" />
            <button type="button" disabled={!draftToken.trim()} onClick={() => setToken(draftToken.trim())}
              className="h-7 rounded-pill border border-line-strong px-3 text-caption text-fg hover:bg-raised disabled:opacity-40">Usar token</button>
          </div>
        </div>
      )}
      <div className="rounded-composer border border-fg/10 bg-composer p-3 focus-within:border-focus/70">
        <label htmlFor="ask-input" className="sr-only">Pregunta a Bob sobre {context.label ?? "este proyecto"}</label>
        <textarea
          id="ask-input"
          ref={area}
          rows={2}
          maxLength={MAX_QUESTION}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKey}
          placeholder={context.kind === "project" ? "Pregunta sobre este repositorio…" : `Pregunta sobre ${context.label ?? "este objeto"}…`}
          className="block max-h-40 min-h-11 w-full resize-none bg-transparent text-caption leading-relaxed text-fg placeholder:text-subtle focus:outline-none"
        />
        <div className="mt-2 flex items-center gap-2">
          <span className="min-w-0 flex-1 truncate font-mono text-micro text-subtle">{blocked ?? "Enter envía · Shift+Enter salto de línea"}</span>
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Enviar pregunta a Bob"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-pill bg-accent text-on-accent shadow-glow transition-[background-color,transform] duration-150 ease-out hover:bg-accent-hover active:scale-95 disabled:bg-disabled disabled:shadow-none"
          >
            <ArrowUp size={16} aria-hidden />
          </button>
        </div>
      </div>
    </form>
  );
}
