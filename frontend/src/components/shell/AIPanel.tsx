import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { lineRange } from "../../lib/format";
import { useWorkspace } from "../../lib/workspace";
import type { AskContext } from "../../types";
import { AskAnswerView, AskComposer } from "../domain/AskBob";
import { IconButton } from "../ui/Button";
import { Eyebrow } from "../ui/Layout";

const BOTTOM_SLACK_PX = 96;

const KIND_LABEL: Record<AskContext["kind"], string> = {
  project: "Project",
  finding: "Finding",
  file: "File",
  function: "Function",
  module: "Module",
};

function suggestions(context: AskContext): string[] {
  const label = context.label ?? "this";
  switch (context.kind) {
    case "finding":
      return [
        `Why is ${context.finding_id} a risk, and what evidence backs it?`,
        `What could break if I fix ${context.finding_id}?`,
        "Which tests should I run after that change?",
      ];
    case "file":
      return [`What does ${label} do, and what depends on it?`, `What risks are there in ${label}?`];
    case "function":
    case "module":
      return [`What depends on ${label}?`, `What would changing ${label} impact?`];
    default:
      return ["What should I migrate first, and why?", "Explain this system's architecture.", "Which tests are missing to migrate safely?"];
  }
}

export function AIPanel({ onClose }: { onClose: () => void }) {
  const { aiContext, askHistory, route, flow, bob, seedComposer } = useWorkspace();
  const scroller = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);
  const asked = useRef(askHistory.length);

  // Only follow the bottom if the person was already there or just asked: if they scroll up to reread
  // while Bob works, the view does not jump when the answer arrives.
  useEffect(() => {
    const el = scroller.current;
    const justAsked = askHistory.length > asked.current;
    asked.current = askHistory.length;
    if (el && (justAsked || atBottom.current)) el.scrollTo({ top: el.scrollHeight });
  }, [askHistory]);

  const onScroll = () => {
    const el = scroller.current;
    if (el) atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_SLACK_PX;
  };

  const disabledReason = !route.jobId
    ? "Open an analysis to ask about its code."
    : flow?.status !== "done"
      ? "Available when the analysis finishes."
      : bob && !(bob.installed && bob.api_key_configured)
        ? "Bob is not available on the server."
        : null;

  return (
    <aside aria-label="IBM Bob assistant" className="relative flex h-full flex-col overflow-hidden bg-surface">
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-line px-4">
        <span aria-hidden className="h-2 w-2 rounded-pill bg-fg-2" />
        <h2 className="font-display text-body text-fg">Bob</h2>
        <span className="text-caption text-subtle">· workspace context</span>
        <IconButton label="Close the Bob panel" className="ml-auto" onClick={onClose}>
          <X size={16} aria-hidden />
        </IconButton>
      </header>

      <div ref={scroller} onScroll={onScroll} className="relative min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-4">
        <section aria-label="Current context" className="rounded-inner border border-line px-3 py-2.5">
          <Eyebrow>Context · {KIND_LABEL[aiContext.kind]}</Eyebrow>
          <p className="mt-1 text-body text-pretty text-fg">{aiContext.label ?? (route.jobId ? "This repository" : "No project open")}</p>
          {aiContext.path && (
            <p className="mt-0.5 truncate font-mono text-caption text-subtle">
              {aiContext.path}{aiContext.line_start ? `:${lineRange(aiContext.line_start, aiContext.line_end ?? aiContext.line_start)}` : ""}
            </p>
          )}
          <p className="mt-2 text-caption text-subtle">Bob reads this analysis's code in read-only mode and cites files and lines; every citation is checked.</p>
        </section>

        {!disabledReason && (
          <section aria-label="Suggested questions">
            <Eyebrow>Ask about this</Eyebrow>
            <ul className="mt-2 space-y-1">
              {suggestions(aiContext).map((text) => (
                <li key={text}>
                  <button type="button" onClick={() => seedComposer(text)} className="w-full rounded-inner px-2.5 py-1.5 text-left text-caption text-fg-2 transition-[background-color,color] duration-150 hover:bg-raised hover:text-fg">
                    {text}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {askHistory.length > 0 && (
          <section aria-label="Conversation" className="space-y-5">
            {askHistory.map((entry) => (
              <article key={entry.id} className="space-y-2 border-t border-line pt-4">
                <p className="text-micro tracking-eyebrow text-subtle uppercase">
                  Question · {KIND_LABEL[entry.context.kind]}{entry.context.finding_id ? ` ${entry.context.finding_id}` : ""}
                </p>
                <p className="text-body text-fg">{entry.question}</p>
                <AskAnswerView entry={entry} />
              </article>
            ))}
          </section>
        )}
      </div>

      <div className="shrink-0 border-t border-line p-3">
        <AskComposer context={aiContext} disabledReason={disabledReason} />
      </div>
    </aside>
  );
}
