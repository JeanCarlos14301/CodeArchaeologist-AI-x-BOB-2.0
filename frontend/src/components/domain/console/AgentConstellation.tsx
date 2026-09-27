import { formatClock, type AgentRun } from "../../../lib/activity";

const W = 640;
const ROW = 58;
const PAD_Y = 30;
const ORCH_X = 118;
const AGENT_X = 404;
const AGENT_W = 208;
const AGENT_H = 42;

/** Summary of a subagent: working (with its clock) or finished (tools, cost, duration). */
export function agentMeta(agent: AgentRun, now: number): string {
  const elapsed = formatClock((agent.status === "done" ? agent.endedAt ?? now : now) - agent.startedAt);
  if (agent.status !== "done") return `working · ${elapsed}`;
  const tools = agent.toolUses != null ? `${agent.toolUses} tools` : "report delivered";
  const cost = agent.cost != null ? ` · ${agent.cost.toFixed(2)} bc` : "";
  const duration = agent.durationMs != null ? ` · ${formatClock(agent.durationMs / 1000)}` : "";
  return `✓ ${tools}${cost}${duration}`;
}

interface Props {
  agents: AgentRun[];
  skills: string[];
  now: number;
  orchestratorBusy: boolean;
  settled: boolean;
}

/**
 * The orchestrator (evidence-auditor) and the subagents it delegates to. A moving dashed edge
 * = subagent working; solid green = it finished and returned its result.
 */
export function AgentConstellation({ agents, skills, now, orchestratorBusy, settled }: Props) {
  const height = Math.max(200, PAD_Y * 2 + Math.max(agents.length, 1) * ROW);
  const cy = height / 2;
  const label = `evidence-auditor orchestrator with ${agents.length} subagents: ${agents.map((agent) => `${agent.name} ${agent.status === "done" ? "finished" : "working"}`).join(", ") || "none"}`;

  return (
    <svg viewBox={`0 0 ${W} ${height}`} role="group" aria-label={label} className="block h-auto w-full">
      <defs>
        <style>{`
          @keyframes ac-flow { to { stroke-dashoffset: -18; } }
          .ac-flow { stroke-dasharray: 4 5; animation: ac-flow 0.9s linear infinite; }
          /* The animation sets the opacity: each one carries its own subtle range. */
          @keyframes ac-halo { 0%,100% { opacity: .06; } 50% { opacity: .18; } }
          @keyframes ac-busy { 0%,100% { opacity: .02; } 50% { opacity: .08; } }
          .ac-halo { animation: ac-halo 1.8s ease-in-out infinite; }
          .ac-busy { animation: ac-busy 1.8s ease-in-out infinite; }
          @media (prefers-reduced-motion: reduce) { .ac-flow, .ac-halo, .ac-busy { animation: none; } }
        `}</style>
      </defs>

      {agents.map((agent, index) => {
        const y = PAD_Y + index * ROW + (height - PAD_Y * 2 - agents.length * ROW) / 2 + ROW / 2;
        const done = agent.status === "done";
        const x1 = ORCH_X + 40;
        const x2 = AGENT_X;
        return (
          <path
            aria-hidden="true"
            key={`edge-${agent.name}-${index}`}
            d={`M${x1},${cy} C${x1 + 110},${cy} ${x2 - 110},${y} ${x2},${y}`}
            fill="none"
            stroke={done ? "var(--color-verified)" : "var(--color-activity)"}
            strokeOpacity={done ? 0.7 : 0.9}
            strokeWidth={done ? 1.5 : 1.25}
            className={done ? undefined : "ac-flow"}
          />
        );
      })}

      <g role="img" aria-label={`evidence-auditor, orchestrator${skills.length ? `; skills: ${skills.join(", ")}` : ""}`}>
        {orchestratorBusy && !settled && <circle cx={ORCH_X} cy={cy} r="50" fill="var(--color-activity)" className="ac-halo" opacity="0.1" />}
        <circle cx={ORCH_X} cy={cy} r="40" fill="var(--color-canvas)" stroke="var(--color-fg)" strokeWidth="1.5" />
        <circle cx={ORCH_X} cy={cy} r="5" fill="var(--color-accent)" />
        <text x={ORCH_X} y={cy + 60} textAnchor="middle" fontSize="12" className="fill-fg font-mono">evidence-auditor</text>
        <text x={ORCH_X} y={cy + 76} textAnchor="middle" fontSize="10.5" className="fill-subtle font-sans">orchestrator · Bob mode</text>
        {skills.slice(0, 2).map((skill, i) => (
          <text key={skill} x={ORCH_X} y={cy - 52 - i * 15} textAnchor="middle" fontSize="10" className="fill-muted font-mono">
            ◇ {skill}
          </text>
        ))}
      </g>

      {agents.length === 0 && (
        <text x={AGENT_X} y={cy + 4} fontSize="12" className="fill-subtle font-sans">
          {settled ? "It did not delegate: it read the code directly" : "No delegation yet"}
        </text>
      )}

      {agents.map((agent, index) => {
        const y = PAD_Y + index * ROW + (height - PAD_Y * 2 - agents.length * ROW) / 2 + ROW / 2;
        const done = agent.status === "done";
        const meta = agentMeta(agent, now);
        return (
          <g
            key={`agent-${agent.name}-${index}`}
            transform={`translate(${AGENT_X},${y - AGENT_H / 2})`}
            tabIndex={0}
            role="img"
            aria-label={[`${agent.name}: ${meta}`, agent.task && `Task: ${agent.task}`, agent.report && `Report: ${agent.report}`].filter(Boolean).join(". ")}
            className="group outline-none"
          >
            <rect x="-4" y="-4" width={AGENT_W + 8} height={AGENT_H + 8} rx="12" fill="none" stroke="var(--color-focus)" strokeWidth="2" className="opacity-0 group-focus-visible:opacity-100" />
            <title>{[agent.name, agent.task && `Task: ${agent.task}`, agent.report && `Report: ${agent.report}`].filter(Boolean).join("\n")}</title>
            <rect width={AGENT_W} height={AGENT_H} rx="8.57" fill="var(--color-canvas)"
              stroke={done ? "var(--color-verified)" : "var(--color-line-strong)"} strokeOpacity={done ? 0.6 : 1} />
            {!done && <rect width={AGENT_W} height={AGENT_H} rx="8.57" fill="var(--color-activity)" className="ac-busy" opacity="0.04" />}
            <text x="12" y="17" fontSize="11.5" className="fill-fg font-mono">{agent.name}</text>
            <text x="12" y="32" fontSize="10.5" className={done ? "fill-verified font-sans" : "fill-muted font-sans"}>{meta}</text>
          </g>
        );
      })}
    </svg>
  );
}

/** List version for narrow containers (mobile): the graph would be unreadable. */
export function AgentList({ agents, skills, now, settled }: Omit<Props, "orchestratorBusy">) {
  return (
    <div className="space-y-3 px-2">
      <p className="text-caption text-fg-2">
        <span className="font-mono text-fg">evidence-auditor</span> · orchestrator
        {skills.length > 0 && <span className="text-subtle"> · {skills.join(", ")}</span>}
      </p>
      {agents.length === 0 ? (
        <p className="text-caption text-subtle">{settled ? "It did not delegate: it read the code directly." : "No delegation yet."}</p>
      ) : (
        <ul className="space-y-2 border-l border-line-strong pl-3">
          {agents.map((agent, index) => (
            <li key={`${agent.name}-${index}`}>
              <p className="flex items-center gap-2 font-mono text-caption text-fg">
                <span aria-hidden className={agent.status === "done" ? "text-verified" : "animate-pulse text-activity"}>{agent.status === "done" ? "✓" : "●"}</span>
                {agent.name}
              </p>
              <p className={`text-caption ${agent.status === "done" ? "text-verified" : "text-muted"}`}>{agentMeta(agent, now)}</p>
              {agent.task && <p className="mt-0.5 line-clamp-2 text-caption text-subtle">{agent.task}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
