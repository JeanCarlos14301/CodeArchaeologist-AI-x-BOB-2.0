import { useEffect, useId, useState } from "react";
import type { AskEntry } from "../../lib/workspace";

/** Bob's state above the composer, derived only from what the chat is really doing. */
export type BobMood = "idle" | "listening" | "working" | "happy" | "error" | "sleeping";

const HAPPY_MS = 2600;
const ERROR_MS = 3600;
const TICK_MS = 1000;

const INK = "var(--color-mascot-ink)";

function Eyes({ mood }: { mood: BobMood }) {
  if (mood === "happy") {
    return (
      <g fill="none" stroke={INK} strokeWidth={3.5} strokeLinecap="round">
        <path d="M40 66 Q46 58 52 66" />
        <path d="M68 66 Q74 58 80 66" />
      </g>
    );
  }
  if (mood === "sleeping") {
    return (
      <g fill="none" stroke={INK} strokeWidth={3.5} strokeLinecap="round">
        <path d="M40 64 Q46 68 52 64" />
        <path d="M68 64 Q74 68 80 64" />
      </g>
    );
  }
  return (
    <g className="bob-pupils">
      <g className="bob-eye">
        <circle cx={46} cy={64} r={6.5} fill={INK} />
        <circle cx={48.2} cy={61.8} r={2} fill="#fff" />
      </g>
      <g className="bob-eye">
        <circle cx={74} cy={64} r={6.5} fill={INK} />
        <circle cx={76.2} cy={61.8} r={2} fill="#fff" />
      </g>
    </g>
  );
}

const MOUTH: Record<BobMood, string> = {
  idle: "M52 76 Q60 82 68 76",
  listening: "M53 76 Q60 81 67 76",
  working: "M54 78 H66",
  happy: "M50 75 Q60 86 70 75 Z",
  error: "M51 79 Q55.5 75 60 79 Q64.5 83 69 79",
  sleeping: "M56 78 H64",
};

/**
 * IBM Bob as an inline SVG so it stays crisp on the black canvas and each part can move on its own
 * (DESIGN.md §4, `BobMascot`). Decorative: the state is told in text next to it.
 */
export function BobMascot({ mood, className }: { mood: BobMood; className?: string }) {
  const helmet = `bob-helmet-${useId().replace(/:/g, "")}`;
  const helmetFill = `url(#${helmet})`;
  return (
    <svg viewBox="0 0 120 128" data-mood={mood} className={`bob-mascot ${className ?? ""}`} aria-hidden focusable="false">
      <defs>
        <linearGradient id={helmet} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--color-mascot-helmet)" />
          <stop offset="1" stopColor="var(--color-mascot-helmet-2)" />
        </linearGradient>
      </defs>
      <g className="bob-body">
        <g className="bob-feet" fill={helmetFill} stroke={INK} strokeWidth={3}>
          <rect x={41} y={117} width={16} height={9} rx={4} />
          <rect x={63} y={117} width={16} height={9} rx={4} />
        </g>
        <g className="bob-arm bob-arm-l">
          <rect x={27} y={91} width={10} height={21} rx={5} fill="#fff" stroke={INK} strokeWidth={3.5} transform="rotate(14 32 93)" />
        </g>
        <g className="bob-arm bob-arm-r">
          <rect x={83} y={91} width={10} height={21} rx={5} fill="#fff" stroke={INK} strokeWidth={3.5} transform="rotate(-14 88 93)" />
        </g>
        <path d="M40 90 H80 V101 C80 111 71 117 60 119 C49 117 40 111 40 101 Z" fill="#fff" stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
        <text className="bob-code" x={60} y={106} textAnchor="middle" fontFamily="var(--font-mono)" fontSize={12} fontWeight={700} fill="var(--color-mascot-helmet)">
          &lt;/&gt;
        </text>

        <g className="bob-head">
          <rect x={16} y={55} width={10} height={20} rx={4} fill="var(--color-mascot-ear)" stroke={INK} strokeWidth={3} />
          <rect x={94} y={55} width={10} height={20} rx={4} fill="var(--color-mascot-ear)" stroke={INK} strokeWidth={3} />
          <rect x={24} y={44} width={72} height={43} rx={15} fill="#fff" stroke={INK} strokeWidth={4} />
          <Eyes mood={mood} />
          <path
            d={MOUTH[mood]}
            fill={mood === "happy" ? INK : "none"}
            stroke={INK}
            strokeWidth={3.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <g className="bob-helmet">
            <path d="M24 44 C24 21 40 8 60 8 C80 8 96 21 96 44 Z" fill={helmetFill} stroke={INK} strokeWidth={3.5} strokeLinejoin="round" />
            <rect x={52} y={6} width={16} height={38} rx={6} fill="var(--color-mascot-ridge)" stroke={INK} strokeWidth={3} />
            <rect x={14} y={39} width={92} height={10} rx={5} fill="var(--color-mascot-helmet)" stroke={INK} strokeWidth={3.5} />
          </g>
        </g>
      </g>
      {mood === "sleeping" && (
        <text className="bob-z" x={102} y={24} fontFamily="var(--font-mono)" fontSize={16} fontWeight={700} fill="var(--color-muted)">z</text>
      )}
    </svg>
  );
}

/**
 * `happy` / `error` for a moment when a question ends while the panel is open. The history already there on
 * mount counts as seen; only the timer dismisses a flash, so re-renders never cut it short or leave it stuck.
 */
function useFlash(latest: AskEntry | undefined): "happy" | "error" | null {
  const key = latest ? `${latest.id}:${latest.status}` : "";
  const [dismissed, setDismissed] = useState(key);
  const mood = !latest || latest.status === "pending" || key === dismissed ? null : latest.status === "done" ? "happy" : "error";

  useEffect(() => {
    if (!mood) return;
    const timer = window.setTimeout(() => setDismissed(key), mood === "happy" ? HAPPY_MS : ERROR_MS);
    return () => window.clearTimeout(timer);
  }, [mood, key]);

  return mood;
}

function useElapsed(since: number | null): number {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (since === null) return;
    const timer = window.setInterval(() => setNow(Date.now() / 1000), TICK_MS);
    return () => window.clearInterval(timer);
  }, [since]);
  return since === null ? 0 : Math.max(0, Math.round(now - since));
}

interface PresenceProps {
  latest: AskEntry | undefined;
  /** Bob's latest real step while it answers (from its live progress). */
  activity: string | undefined;
  listening: boolean;
  sleeping: boolean;
  subject: string;
}

/** Bob sitting on the composer: its mood and one line of what it is doing right now. */
export function BobPresence({ latest, activity, listening, sleeping, subject }: PresenceProps) {
  const flash = useFlash(latest);
  const working = latest?.status === "pending";
  const elapsed = useElapsed(working && latest ? latest.startedAt : null);

  const mood: BobMood = working ? "working" : flash ?? (sleeping ? "sleeping" : listening ? "listening" : "idle");

  const caption: Record<BobMood, string> = {
    idle: `Ask me about ${subject}.`,
    listening: "Press Enter and I'll start reading.",
    working: activity ?? "Thinking…",
    happy: "Answer ready.",
    error: "That didn't work. Try again.",
    sleeping: "Resting.",
  };

  return (
    <div className="relative z-10 -mb-1 flex items-end gap-2 pl-3">
      <BobMascot mood={mood} className="h-12 w-auto shrink-0" />
      <p className="flex min-w-0 items-baseline gap-1.5 pb-3.5 text-caption text-muted">
        <span key={caption[mood]} className="min-w-0 animate-enter truncate">{caption[mood]}</span>
        {working && <span className="shrink-0 font-mono text-micro text-subtle tabular-nums">{elapsed} s</span>}
      </p>
    </div>
  );
}
