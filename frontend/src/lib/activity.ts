import type { PipelineEvent, Severity, StageId } from "../types";

/**
 * Model of the analysis activity built from the backend events (pure function).
 * To replay a session, build it with the events whose `t` ≤ the playhead.
 */

export const STAGE_ORDER: StageId[] = ["preparing", "auditing", "validating", "migration", "done"];

export interface Check {
  name: string;
  value: string;
  limit: string;
}

export interface Inventory {
  files: number;
  bytes: number;
  python_lines: number;
  languages: { name: string; files: number }[];
  top_dirs: { name: string; files: number }[];
  excluded: string[];
  sha256: string;
}

export interface AgentRun {
  name: string;
  task: string | null;
  status: "running" | "done";
  startedAt: number;
  endedAt: number | null;
  toolUses: number | null;
  turns: number | null;
  cost: number | null;
  durationMs: number | null;
  /** First sentence of the report the subagent returned to the orchestrator. */
  report: string | null;
}

export interface FeedItem {
  seq: number;
  t: number;
  kind: string;
  actor: string;
  title: string;
  detail: string | null;
  target: string | null;
}

export interface PlanItem {
  state: "done" | "active" | "pending";
  text: string;
}

export interface EvidenceCheckItem {
  seq: number;
  t: number;
  findingId: string;
  status: "valid" | "invalid";
  path: string | null;
  lineStart: number | null;
  lineEnd: number | null;
  severity: Severity | null;
  reason: string | null;
}

export interface TestRun {
  seq: number;
  target: "legacy" | "modern";
  name: string;
  status: "passed" | "failed" | "not_run";
  durationMs: number;
  reason: string | null;
}

export interface ActivityModel {
  stages: Record<StageId, { start: number | null; end: number | null; events: number }>;
  checks: Check[];
  inventory: Inventory | null;
  bob: {
    maxCost: number | null;
    exploreCost: number | null;
    subagentsEnabled: boolean | null;
    turns: number;
    tools: number;
    plan: PlanItem[];
    agents: AgentRun[];
    skills: string[];
    feed: FeedItem[];
    finalize: FeedItem | null;
    result: { cost: number | null; durationMs: number | null; toolCalls: number | null } | null;
    answered: boolean;
    recorded: boolean;
  };
  evidence: { checks: EvidenceCheckItem[]; summary: { accepted: number; rejected: number; valid: number; total: number; riskScored: number; pertDays: number | null } | null };
  migration: { tests: TestRun[]; skipped: string | null; summary: { status: string; endpoint: string } | null };
  done: { findings: number; bySeverity: Record<string, number>; evidenceValid: number; evidenceTotal: number; cost: number | null; durationMs: number | null } | null;
  failure: { stage: StageId; message: string } | null;
  lastT: number;
}

const num = (value: unknown): number | null => (typeof value === "number" && Number.isFinite(value) ? value : null);
const str = (value: unknown): string | null => (typeof value === "string" && value.length > 0 ? value : null);

function emptyModel(): ActivityModel {
  return {
    stages: Object.fromEntries(STAGE_ORDER.map((stage) => [stage, { start: null, end: null, events: 0 }])) as ActivityModel["stages"],
    checks: [],
    inventory: null,
    bob: { maxCost: null, exploreCost: null, subagentsEnabled: null, turns: 0, tools: 0, plan: [], agents: [], skills: [], feed: [], finalize: null, result: null, answered: false, recorded: false },
    evidence: { checks: [], summary: null },
    migration: { tests: [], skipped: null, summary: null },
    done: null,
    failure: null,
    lastT: 0,
  };
}

const FEED_KINDS = new Set(["bob.tool", "bob.thinking", "bob.skill", "bob.subagent.start", "bob.subagent.end", "bob.subagent.report", "bob.plan", "bob.finalize", "bob.answer", "bob.writing", "bob.tool.error"]);

export function buildActivity(events: PipelineEvent[]): ActivityModel {
  const model = emptyModel();
  for (const event of events) {
    const stage = model.stages[event.stage];
    if (stage) {
      stage.start = stage.start === null ? event.t : Math.min(stage.start, event.t);
      stage.end = Math.max(stage.end ?? event.t, event.t);
      stage.events += 1;
    }
    model.lastT = Math.max(model.lastT, event.t);
    if (event.recorded) model.bob.recorded = true;
    apply(model, event);
  }
  return model;
}

/** Replaces (without mutating it) the first subagent that matches; false if there is none. */
function patchAgent(model: ActivityModel, match: (agent: AgentRun) => boolean, patch: Partial<AgentRun>): boolean {
  const index = model.bob.agents.findIndex(match);
  if (index < 0) return false;
  model.bob.agents = model.bob.agents.map((agent, i) => (i === index ? { ...agent, ...patch } : agent));
  return true;
}

function apply(model: ActivityModel, event: PipelineEvent): void {
  const d = event.data;
  if (FEED_KINDS.has(event.kind)) {
    const chars = num(d.chars);
    const title = (event.kind === "bob.writing" || event.kind === "bob.answer" || event.kind === "bob.subagent.report") && chars
      ? `${event.title} · ${chars.toLocaleString("en")} characters`
      : event.title;
    model.bob.feed.push({ seq: event.seq, t: event.t, kind: event.kind, actor: event.actor, title, detail: event.detail, target: str(d.target) });
  }
  switch (event.kind) {
    case "ingest.check":
      model.checks.push({ name: event.title, value: str(d.value) ?? "", limit: str(d.limit) ?? "" });
      break;
    case "inventory":
      model.inventory = {
        files: num(d.files) ?? 0,
        bytes: num(d.bytes) ?? 0,
        python_lines: num(d.python_lines) ?? 0,
        languages: Array.isArray(d.languages) ? (d.languages as Inventory["languages"]) : [],
        top_dirs: Array.isArray(d.top_dirs) ? (d.top_dirs as Inventory["top_dirs"]) : [],
        excluded: Array.isArray(d.excluded) ? (d.excluded as string[]) : [],
        sha256: str(d.sha256) ?? "",
      };
      break;
    case "bob.start":
      model.bob.maxCost = num(d.max_cost);
      model.bob.exploreCost = num(d.explore_cost);
      model.bob.subagentsEnabled = typeof d.subagents === "boolean" ? d.subagents : null;
      break;
    case "bob.turn":
      model.bob.turns = Math.max(model.bob.turns, num(d.turn) ?? 0);
      break;
    case "bob.tool":
      model.bob.tools += 1;
      break;
    case "bob.skill":
      if (str(d.skill) && !model.bob.skills.includes(d.skill as string)) model.bob.skills.push(d.skill as string);
      break;
    case "bob.plan":
      if (Array.isArray(d.items)) model.bob.plan = d.items as PlanItem[];
      break;
    case "bob.subagent.start":
      model.bob.agents.push({
        name: str(d.agent) ?? "subagent", task: event.detail, status: "running", startedAt: event.t,
        endedAt: null, toolUses: null, turns: null, cost: null, durationMs: null, report: null,
      });
      break;
    // Bob gives no id when a subagent starts: each report and each closing fills the first subagent
    // with that name that does not have it yet, never overwriting one that is already complete.
    case "bob.subagent.report": {
      const name = str(d.agent) ?? "subagent";
      const report = event.detail ?? "";
      if (!patchAgent(model, (agent) => agent.name === name && agent.report === null, { report })) {
        // Without the Bob log there was no subagent_start: the report is enough to know it worked.
        model.bob.agents = [...model.bob.agents, {
          name, task: null, status: "done", startedAt: event.t, endedAt: event.t,
          toolUses: null, turns: null, cost: null, durationMs: null, report,
        }];
      }
      break;
    }
    case "bob.subagent.end": {
      const name = str(d.agent) ?? "subagent";
      patchAgent(model, (agent) => agent.name === name && agent.status === "running", {
        status: "done", endedAt: event.t, toolUses: num(d.tool_uses), turns: num(d.turns), cost: num(d.cost), durationMs: num(d.duration_ms),
      });
      break;
    }
    case "bob.finalize":
      model.bob.finalize = model.bob.feed[model.bob.feed.length - 1] ?? null;
      break;
    case "bob.answer":
      model.bob.answered = true;
      break;
    case "bob.result":
      model.bob.result = { cost: num(d.cost), durationMs: num(d.duration_ms), toolCalls: num(d.tool_calls) };
      break;
    case "evidence.check":
      model.evidence.checks.push({
        seq: event.seq, t: event.t, findingId: str(d.finding_id) ?? "?", status: d.status === "valid" ? "valid" : "invalid",
        path: str(d.path), lineStart: num(d.line_start), lineEnd: num(d.line_end), severity: (str(d.severity) as Severity | null), reason: event.detail,
      });
      break;
    case "evidence.summary":
      model.evidence.summary = {
        accepted: num(d.accepted) ?? 0, rejected: num(d.rejected) ?? 0, valid: num(d.valid) ?? 0, total: num(d.total) ?? 0,
        riskScored: num(d.risk_scored) ?? 0, pertDays: num(d.pert_expected_days),
      };
      break;
    case "tests.result":
      model.migration.tests.push({
        seq: event.seq, target: d.target === "modern" ? "modern" : "legacy", name: str(d.name) ?? event.title,
        status: d.status === "passed" ? "passed" : d.status === "failed" ? "failed" : "not_run", durationMs: num(d.duration_ms) ?? 0, reason: event.detail,
      });
      break;
    case "tests.skipped":
      model.migration.skipped = event.detail ?? event.title;
      break;
    case "tests.summary":
      model.migration.summary = { status: str(d.status) ?? "", endpoint: str(d.endpoint) ?? "" };
      break;
    case "dossier.ready":
      model.done = {
        findings: num(d.findings) ?? 0, bySeverity: (d.by_severity as Record<string, number>) ?? {},
        evidenceValid: num(d.evidence_valid) ?? 0, evidenceTotal: num(d.evidence_total) ?? 0,
        cost: num(d.bob_cost), durationMs: num(d.bob_duration_ms),
      };
      break;
    case "pipeline.failed":
      model.failure = { stage: event.stage, message: event.detail ?? event.title };
      break;
  }
}

/** One-line summary per stage for the rail (only figures present in the events). */
export function stageMetric(model: ActivityModel, stage: StageId): string | null {
  switch (stage) {
    case "preparing":
      return model.inventory ? `${model.inventory.files} files · ${model.inventory.python_lines.toLocaleString("en")} Python lines` : null;
    case "auditing": {
      const parts: string[] = [];
      if (model.bob.tools) parts.push(`${model.bob.tools} reads and searches`);
      if (model.bob.agents.length) parts.push(`${model.bob.agents.length} subagent${model.bob.agents.length === 1 ? "" : "s"}`);
      if (model.bob.result?.cost != null) parts.push(`${model.bob.result.cost.toFixed(2)} bc`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "validating": {
      if (model.evidence.summary) return `${model.evidence.summary.valid}/${model.evidence.summary.total} citations verified`;
      const valid = model.evidence.checks.filter((c) => c.status === "valid").length;
      return model.evidence.checks.length ? `${valid}/${model.evidence.checks.length} citations…` : null;
    }
    case "migration":
      if (model.migration.skipped) return "Uploaded code never runs";
      return model.migration.tests.length
        ? `${model.migration.tests.filter((t) => t.status === "passed").length}/${model.migration.tests.length} tests pass`
        : null;
    case "done":
      return model.done ? `${model.done.findings} findings with evidence` : null;
  }
}

export const formatClock = (seconds: number) => {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
