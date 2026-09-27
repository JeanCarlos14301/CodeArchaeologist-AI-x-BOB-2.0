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
/** What Bob DOES (reads, searches, skills, reasoning); without its turns or the session closing. */
export const visibleSteps = (steps: AskStep[]): AskStep[] => steps.filter((step) => !BOOKKEEPING.has(step.kind));

const asWork = (steps: AskStep[], startedAt: number): BobWorkEvent[] =>
  visibleSteps(steps).map((step) => ({ t: startedAt + step.t, kind: step.kind, message: step.message, detail: step.detail, data: step.data }));

/** How Bob reached the answer: the real steps, folded so they do not take over the chat. */
function HowBobGotThere({ steps: all, startedAt }: { steps: AskStep[]; startedAt: number }) {
  const steps = visibleSteps(all);
  if (steps.length === 0) return null;
  const counters = bobCounters(asWork(steps, startedAt));
  return (
    <details className="group rounded-inner border border-line-subtle px-3 py-2">
      <summary className="cursor-pointer list-none text-caption text-muted marker:hidden hover:text-fg">
        <span aria-hidden className="mr-1.5 inline-block transition-transform duration-150 group-open:rotate-90">›</span>
        How Bob reached this answer · {steps.length} {steps.length === 1 ? "step" : "steps"}
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
  { key: "facts", label: "Detected facts", tone: "text-verified" },
  { key: "inferences", label: "Inferences", tone: "text-warning" },
  { key: "recommendations", label: "Recommendations", tone: "text-fg" },
];

/** Bob's answer with facts, inferences, recommendations and unknowns (PRODUCT.md §20). */
export function AskAnswerView({ entry }: { entry: AskEntry }) {
  const { go } = useWorkspace();
  if (entry.status === "pending") {
    return <BobWork compact title="Bob is working on your question" events={asWork(entry.progress, entry.startedAt)} since={entry.startedAt} />;
  }
  if (entry.status === "error" || !entry.answer) {
    return (
      <p role="alert" className="text-caption text-danger">
        <span aria-hidden>✗ </span>{entry.error ?? "Bob did not answer."}
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
                reason={ref.verified ? "The file and the lines exist in the repository" : "The citation does not exist in the analyzed repository"}
                onOpen={ref.verified ? () => openRef(ref.path, ref.line_start) : undefined} />
            ))}
          </span>
        )}
      </li>
    ));

  return (
    <div className="space-y-3" aria-live="polite">
      <p className="text-body text-pretty text-fg"><InlineText text={answer.summary} /></p>
      {!answer.structured && <p className="text-caption text-warning">Bob answered in free text: facts could not be separated from inferences and citations could not be verified.</p>}
      {SECTIONS.map((section) => answer[section.key].length > 0 && (
        <section key={section.key}>
          <Eyebrow className={section.tone}>{section.label}</Eyebrow>
          <ul className="mt-1.5 space-y-2">{claims(answer[section.key])}</ul>
        </section>
      ))}
      {answer.unknowns.length > 0 && (
        <section>
          <Eyebrow>Unknown with the available code</Eyebrow>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-caption text-muted">
            {answer.unknowns.map((item, i) => <li key={i}><InlineText text={item} /></li>)}
          </ul>
        </section>
      )}
      <HowBobGotThere steps={entry.progress} startedAt={entry.startedAt} />
      <p className="font-mono text-micro text-subtle">IBM Bob · ask mode · {formatCost(answer.bob_cost)} · {formatSeconds(answer.bob_duration_ms)}</p>
    </div>
  );
}

const MIN_QUESTION = 3;
const MAX_QUESTION = 800;

/** Question composer: carbon shell + orange orb (reference "Hero Prompt Composer"). */
export function AskComposer({ context, disabledReason }: { context: AskContext; disabledReason: string | null }) {
  const { ask, askHistory, token, setToken, tokenRequired, hasAccess, composerSeed, clearComposerSeed } = useWorkspace();
  const [text, setText] = useState("");
  const [draftToken, setDraftToken] = useState("");
  const area = useRef<HTMLTextAreaElement>(null);
  const pending = askHistory.some((entry) => entry.status === "pending");

  useEffect(() => {
    if (!composerSeed) return;
    setText(composerSeed.text);
    // preventScroll: the browser would otherwise scroll every ancestor (up to the page) to show the textarea.
    area.current?.focus({ preventScroll: true });
    // The seed is consumed: if the panel remounts after the answer, the previous question does not come back.
    clearComposerSeed();
  }, [composerSeed, clearComposerSeed]);

  const question = text.trim();
  const blocked = disabledReason ?? (pending ? "Bob is answering the previous question." : null);
  const canSend = !blocked && hasAccess && question.length >= MIN_QUESTION;

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
      {tokenRequired && !token && !disabledReason && (
        <div className="rounded-inner border border-line px-3 py-2.5">
          <label className="block text-caption text-muted" htmlFor="ask-token">Access token · each question spends bobcoins</label>
          <div className="mt-1.5 flex gap-2">
            <input id="ask-token" type="password" autoComplete="off" value={draftToken} onChange={(event) => setDraftToken(event.target.value)}
              className="h-7 min-w-0 flex-1 rounded-pill border border-line bg-control px-3 font-mono text-caption text-fg placeholder:text-subtle focus:border-focus focus:outline-none" placeholder="X-Live-Token" />
            <button type="button" disabled={!draftToken.trim()} onClick={() => setToken(draftToken.trim())}
              className="h-7 rounded-pill border border-line-strong px-3 text-caption text-fg hover:bg-raised disabled:opacity-40">Use token</button>
          </div>
        </div>
      )}
      <div className="rounded-composer border border-fg/10 bg-composer p-3 focus-within:border-focus/70">
        <label htmlFor="ask-input" className="sr-only">Ask Bob about {context.label ?? "this project"}</label>
        <textarea
          id="ask-input"
          ref={area}
          rows={2}
          maxLength={MAX_QUESTION}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKey}
          placeholder={context.kind === "project" ? "Ask about this repository…" : `Ask about ${context.label ?? "this object"}…`}
          className="block max-h-40 min-h-11 w-full resize-none bg-transparent text-caption leading-relaxed text-fg placeholder:text-subtle focus:outline-none"
        />
        <div className="mt-2 flex items-center gap-2">
          <span className="min-w-0 flex-1 truncate font-mono text-micro text-subtle">{blocked ?? "Enter sends · Shift+Enter new line"}</span>
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Send the question to Bob"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-pill bg-accent text-on-accent shadow-glow transition-[background-color,transform] duration-150 ease-out hover:bg-accent-hover active:scale-95 disabled:bg-disabled disabled:shadow-none"
          >
            <ArrowUp size={16} aria-hidden />
          </button>
        </div>
      </div>
    </form>
  );
}
