import { useEffect, useMemo, useRef, useState } from "react";
import { BookOpen, CheckCircle2, CornerDownLeft, FileText, GitFork, ListChecks, MessageSquareText, PenLine, RotateCcw, Search, TriangleAlert, type LucideIcon } from "lucide-react";
import { formatClock, type ActivityModel, type FeedItem } from "../../../lib/activity";
import { Eyebrow } from "../../ui/Layout";
import { AgentConstellation, AgentList } from "./AgentConstellation";

const ICON: Record<string, LucideIcon> = {
  "bob.tool": FileText,
  "bob.skill": BookOpen,
  "bob.plan": ListChecks,
  "bob.subagent.start": GitFork,
  "bob.subagent.end": CheckCircle2,
  "bob.subagent.report": CornerDownLeft,
  "bob.thinking": MessageSquareText,
  "bob.finalize": RotateCcw,
  "bob.answer": PenLine,
  "bob.writing": PenLine,
  "bob.tool.error": TriangleAlert,
};

const PLAN_MARK = { done: { glyph: "✓", tone: "text-verified" }, active: { glyph: "●", tone: "text-activity" }, pending: { glyph: "○", tone: "text-subtle" } };

interface Props {
  model: ActivityModel;
  now: number;
  settled: boolean;
  /** Live only: announces a feed summary to screen readers (never during a replay). */
  announce: boolean;
}

const ANNOUNCE_EVERY_MS = 4000;

/** Feed summary for screen readers: at most one every 4 s, never one announcement per action. */
function useFeedAnnouncement(feed: FeedItem[], enabled: boolean): string {
  const [message, setMessage] = useState("");
  const announced = useRef(feed.length);
  const lastAt = useRef(0);
  useEffect(() => {
    if (!enabled) {
      announced.current = feed.length;
      return;
    }
    const pending = feed.length - announced.current;
    if (pending <= 0) return;
    const wait = Math.max(0, lastAt.current + ANNOUNCE_EVERY_MS - Date.now());
    const timer = window.setTimeout(() => {
      const fresh = feed.length - announced.current;
      if (fresh <= 0) return;
      announced.current = feed.length;
      lastAt.current = Date.now();
      setMessage(`${fresh} new Bob ${fresh === 1 ? "action" : "actions"}. Latest: ${feed[feed.length - 1].title}`);
    }, wait);
    return () => window.clearTimeout(timer);
  }, [feed, enabled]);
  return message;
}

/** Stage 2: how Bob reasons — plan, delegation to subagents and every action it takes. */
export function AgentsPanel({ model, now, settled, announce }: Props) {
  const bob = model.bob;
  const feed = useMemo(() => compactFeed(bob.feed), [bob.feed]);
  const announcement = useFeedAnnouncement(feed, announce);
  const scroller = useRef<HTMLOListElement>(null);
  const running = bob.agents.filter((agent) => agent.status === "running").length;
  const subagentCost = bob.agents.reduce((sum, agent) => sum + (agent.cost ?? 0), 0);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [feed.length]);

  const stats = [
    { label: "Orchestrator turns", value: bob.turns || "—" },
    { label: "Reads and searches", value: bob.tools || "—" },
    { label: "Subagents", value: bob.agents.length ? `${bob.agents.length - running}/${bob.agents.length} finished` : "—" },
    {
      label: bob.result?.cost != null ? "Session cost" : "Reported cost",
      value: bob.result?.cost != null ? `${bob.result.cost.toFixed(2)} bc` : subagentCost ? `≥ ${subagentCost.toFixed(2)} bc` : "—",
      hint: bob.maxCost != null ? `cap ${bob.maxCost} bc` : undefined,
    },
  ];

  return (
    <div className="space-y-6">
      {bob.recorded && (
        <p className="rounded-inner border border-line px-3 py-2 text-caption text-muted">
          A real IBM Bob session, recorded and replayed at its original pace (sped up). It spends no bobcoins.
        </p>
      )}
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 @2xl:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label}>
            <dt className="text-micro tracking-eyebrow text-subtle uppercase">{stat.label}</dt>
            <dd className="mt-1 font-mono text-body text-fg tabular-nums">
              {stat.value}
              {stat.hint && <span className="ml-1.5 text-caption text-subtle">· {stat.hint}</span>}
            </dd>
          </div>
        ))}
      </dl>

      <section aria-label="Orchestrator and subagents" className="rounded-panel border border-line bg-surface px-2 py-3">
        <div className="hidden @xl:block">
          <AgentConstellation agents={bob.agents} skills={bob.skills} now={now} orchestratorBusy={!bob.result} settled={settled || !!bob.result} />
        </div>
        <div className="@xl:hidden">
          <AgentList agents={bob.agents} skills={bob.skills} now={now} settled={settled || !!bob.result} />
        </div>
        {bob.finalize && (
          <p className="mx-3 mt-2 flex items-start gap-2 text-caption text-warning">
            <RotateCcw size={13} aria-hidden className="mt-0.5 shrink-0" />
            {bob.finalize.title}. {bob.finalize.detail}
          </p>
        )}
      </section>

      <div className="grid grid-cols-1 gap-6 @3xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <section aria-label="Bob's plan">
          <Eyebrow>Bob's plan</Eyebrow>
          {bob.plan.length === 0 ? (
            <p className="mt-2 text-caption text-subtle">{settled ? "Bob did not publish a plan in this session." : "Waiting for the plan…"}</p>
          ) : (
            <ol className="mt-2 space-y-2">
              {bob.plan.map((item, index) => (
                <li key={`${index}-${item.text}`} className="grid grid-cols-[1rem_1fr] gap-x-2 text-caption">
                  <span aria-hidden className={`${PLAN_MARK[item.state].tone} ${item.state === "active" && !settled ? "animate-pulse" : ""}`}>{PLAN_MARK[item.state].glyph}</span>
                  <span className={item.state === "pending" ? "text-subtle" : "text-fg-2"}>
                    {item.text}
                    <span className="sr-only"> ({item.state === "done" ? "done" : item.state === "active" ? "in progress" : "pending"})</span>
                  </span>
                </li>
              ))}
            </ol>
          )}
          {bob.skills.length > 0 && (
            <>
              <Eyebrow className="mt-5">Skills activated</Eyebrow>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {bob.skills.map((skill) => <li key={skill} className="rounded-pill border border-line px-2.5 py-0.5 font-mono text-caption text-fg-2">{skill}</li>)}
              </ul>
            </>
          )}
        </section>

        <section aria-label="Bob's reasoning and actions">
          <Eyebrow>Reasoning and actions · {feed.length}</Eyebrow>
          <p role="status" className="sr-only">{announcement}</p>
          <ol ref={scroller} role="log" aria-live="off" aria-label="Bob's actions in chronological order" className="mt-2 max-h-[26rem] space-y-1 overflow-y-auto pr-1">
            {feed.length === 0 && <li className="text-caption text-subtle">{settled ? "No activity recorded." : "Bob is starting…"}</li>}
            {feed.map((item) => <FeedRow key={item.seq} item={item} />)}
          </ol>
        </section>
      </div>
    </div>
  );
}

function FeedRow({ item }: { item: FeedItem }) {
  const Icon = item.kind === "bob.tool" && /^(Search|Busc)/.test(item.title) ? Search : ICON[item.kind] ?? FileText;
  const thinking = item.kind === "bob.thinking";
  const delegate = item.kind === "bob.subagent.start" || item.kind === "bob.subagent.end" || item.kind === "bob.subagent.report";
  return (
    <li className="grid animate-enter grid-cols-[2.75rem_1rem_1fr] items-start gap-x-2 py-1 text-caption">
      <span className="pt-px font-mono text-micro text-subtle tabular-nums">{formatClock(item.t)}</span>
      <Icon size={13} aria-hidden className={`mt-0.5 ${delegate ? "text-fg" : item.kind === "bob.tool.error" ? "text-danger" : "text-subtle"}`} />
      <span className="min-w-0">
        {thinking ? (
          <span className="block border-l border-line-strong pl-2 text-pretty text-fg-2">{item.detail}</span>
        ) : (
          <>
            <span className={delegate ? "text-fg" : "text-fg-2"}>{item.title}</span>
            {item.detail && item.kind !== "bob.plan" && <span className="mt-0.5 block text-pretty text-subtle">{item.detail}</span>}
            {item.kind === "bob.plan" && item.detail && <span className="text-subtle"> · {item.detail}</span>}
          </>
        )}
      </span>
    </li>
  );
}

/** A single row for consecutive writing progress (it updates instead of repeating). */
function compactFeed(feed: FeedItem[]): FeedItem[] {
  const out: FeedItem[] = [];
  for (const item of feed) {
    const previous = out[out.length - 1];
    if (item.kind === "bob.writing" && previous?.kind === "bob.writing") out[out.length - 1] = item;
    else out.push(item);
  }
  return out;
}
