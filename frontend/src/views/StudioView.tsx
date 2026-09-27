import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "../api";
import { AssessmentPanel } from "../components/domain/studio/AssessmentPanel";
import { BobWork } from "../components/domain/BobWork";
import { ImplementationPanel } from "../components/domain/studio/ImplementationPanel";
import { PlanGraph } from "../components/domain/studio/PlanGraph";
import { StackBoard } from "../components/domain/studio/StackBoard";
import { EMPTY_DRAFT, TransformBoard, type Draft } from "../components/domain/studio/TransformBoard";
import { Section } from "../components/ui/Layout";
import { EmptyState, ErrorState, Loading } from "../components/ui/States";
import { useWorkspace } from "../lib/workspace";
import type { AssessRequest, StackReport, StudioPhase, StudioState } from "../types";

const POLL_MS = 2000;
const WORKING: StudioPhase[] = ["assessing", "planning", "implementing"];

const STEPS = [
  { id: "stack", label: "Stack" },
  { id: "targets", label: "Targets" },
  { id: "assessment", label: "Assessment" },
  { id: "plan", label: "Plan" },
  { id: "implementation", label: "Implementation" },
] as const;

function stepStatus(state: StudioState | null, id: (typeof STEPS)[number]["id"]): "done" | "active" | "pending" | "failed" {
  const phase = state?.phase ?? "idle";
  const has = { assessment: !!state?.assessment, plan: !!state?.plan, implementation: !!state?.implementation };
  const done = { stack: true, targets: !!state?.request, assessment: has.assessment, plan: has.plan, implementation: has.implementation && phase === "implemented" };
  if (phase === "failed" && !done[id] && (id === "assessment" && !has.assessment || id === "plan" && has.assessment && !has.plan || id === "implementation" && has.plan)) return "failed";
  if (done[id]) return "done";
  const working = { assessment: phase === "assessing", plan: phase === "planning", implementation: phase === "implementing", stack: false, targets: false };
  if (working[id]) return "active";
  const firstOpen = STEPS.find((step) => !done[step.id])?.id;
  return firstOpen === id ? "active" : "pending";
}

/** Modernization Studio: measure the stack, decide targets, understand the impact, plan and implement with Bob. */
export function StudioView() {
  const { flow, token, setToken, tokenRequired, hasAccess, go, offline } = useWorkspace();
  const jobId = flow?.id ?? "";
  const [stack, setStack] = useState<StackReport | null>(null);
  const [stackError, setStackError] = useState<string | null>(null);
  const [state, setState] = useState<StudioState | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  // Answers in progress to the questions of the current assessment (by question text).
  const [qa, setQa] = useState<Record<string, string>>({});
  const seeded = useRef<string | null>(null);

  // Current token: if the person changes the token with a request in flight, the old response is discarded.
  const currentToken = useRef(token);
  useEffect(() => {
    currentToken.current = token;
  }, [token]);
  const refresh = useCallback(() => api.studio(jobId, token)
    .then((next) => { if (currentToken.current === token) setState(next); })
    .catch((err: Error) => { if (currentToken.current === token) setActionError(err.message); }), [jobId, token]);

  useEffect(() => {
    let cancelled = false;
    setStack(null);
    setStackError(null);
    api.stack(jobId, token)
      .then((next) => { if (!cancelled) setStack(next); })
      .catch((err: Error) => { if (!cancelled) setStackError(err.message); });
    void refresh();
    return () => { cancelled = true; };
  }, [jobId, token, refresh]);

  // When an analysis with previous decisions opens, they are restored on the board.
  useEffect(() => {
    if (!state?.request || seeded.current === jobId) return;
    seeded.current = jobId;
    setDraft({
      mode: state.request.mode,
      mappings: Object.fromEntries(state.request.mappings.map((m) => [m.from_id, m.to_id])),
      business_context: state.request.business_context,
      priorities: state.request.priorities,
    });
  }, [state, jobId]);

  const working = !!state && WORKING.includes(state.phase);
  useEffect(() => {
    if (!working) return;
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [working, refresh]);

  const run = async (action: () => Promise<StudioState>) => {
    setBusy(true);
    setActionError(null);
    try {
      setState(await action());
    } catch (err) {
      setActionError(err instanceof ApiError && err.status === 403 ? "The token is not valid." : (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const history = state?.request?.answers ?? [];

  /** Assessment request with the current decisions and everything the person already answered Bob. */
  const buildRequest = (fresh: { question: string; answer: string }[]): AssessRequest => {
    const byQuestion = new Map([...history, ...fresh].map((item) => [item.question, item]));
    return {
      mode: draft.mode,
      mappings: draft.mode === "chosen" ? Object.entries(draft.mappings).map(([from_id, to_id]) => ({ from_id, to_id })) : [],
      business_context: draft.business_context.trim(),
      priorities: draft.priorities,
      answers: [...byQuestion.values()].slice(-10),
    };
  };

  const assess = () => void run(() => api.studioAssess(jobId, buildRequest([]), token));

  const reassess = () => {
    const fresh = Object.entries(qa)
      .map(([question, answer]) => ({ question, answer: answer.trim() }))
      .filter((item) => item.answer.length > 0);
    setQa({});
    void run(() => api.studioAssess(jobId, buildRequest(fresh), token));
  };

  const download = useCallback(async (name: "modernized.zip" | "migration.diff") => {
    const blob = await api.studioDownload(jobId, name, token);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  }, [jobId, token]);

  const loadDiff = useCallback(async () => (await api.studioDownload(jobId, "migration.diff", token)).text(), [jobId, token]);
  const openFile = (path: string, line?: number) => go("repository", { file: path, line: line ?? null });
  const runs = useMemo(() => {
    const map: Record<string, "done" | "failed" | "skipped" | "running"> = {};
    for (const step of state?.implementation?.steps ?? []) map[step.step_id] = step.status;
    return map;
  }, [state?.implementation]);

  if (offline) return <ErrorState title="No connection to the backend." message="GET /api/audits did not answer." hint="Start the server and reload the page." />;
  if (stackError) return <ErrorState title="The stack could not be measured." message={stackError} hint="The code for this analysis may have been removed from the server." onRetry={() => setToken(token)} />;
  if (!stack || !state) return <Loading label="Measuring the project's stack…" />;

  const phase = state.phase;
  const hasAssessment = !!state.assessment;
  const editable = !working;

  return (
    <div>
      <ol className="mb-2 flex flex-wrap gap-x-6 gap-y-2 border-b border-line pb-4" aria-label="Studio progress">
        {STEPS.map((step, index) => {
          const status = stepStatus(state, step.id);
          const tone = status === "done" ? "text-verified" : status === "failed" ? "text-danger" : status === "active" ? "text-fg" : "text-subtle";
          return (
            <li key={step.id} aria-current={status === "active" ? "step" : undefined} className={`flex items-center gap-2 text-caption ${tone}`}>
              <span aria-hidden className="font-mono">{status === "done" ? "✓" : status === "failed" ? "✗" : status === "active" ? "●" : String(index + 1).padStart(2, "0")}</span>
              {step.label}
              <span className="sr-only">{status === "done" ? ", complete" : status === "failed" ? ", failed" : status === "active" ? ", in progress" : ", pending"}</span>
            </li>
          );
        })}
      </ol>

      <Section eyebrow="01 · What you use today" title="Stack detected in your project">
        <StackBoard stack={stack} />
      </Section>

      <Section eyebrow="02 · Where you want to go" title="Migration targets">
        <fieldset disabled={!editable} className="min-w-0 border-0 p-0">
          <TransformBoard
            stack={stack}
            draft={draft}
            onChange={setDraft}
            onSubmit={assess}
            busy={busy || phase === "assessing"}
            needsToken={tokenRequired}
            token={token}
            onToken={setToken}
            resetsWork={hasAssessment}
          />
        </fieldset>
        {actionError && <div className="mt-4"><ErrorState title="The action did not complete." message={actionError} onRetry={() => setActionError(null)} retryLabel="Dismiss" /></div>}
      </Section>

      {phase === "assessing" && (
        <Section eyebrow="03 · Assessment" title="Bob is assessing">
          <BobWork title="Bob reads your code and weighs what is gained and what is traded away" events={state.events.filter((event) => event.phase === "assessing")} />
        </Section>
      )}
      {phase === "failed" && state.error && (
        <Section eyebrow="Something went wrong" title="The last operation with Bob failed">
          <ErrorState
            title="Bob could not complete the step."
            message={state.error}
            hint="No work was wasted: what was already generated is still available. You can retry."
            onRetry={() => void run(() => (!state.assessment ? api.studioAssess(jobId, { mode: draft.mode, mappings: Object.entries(draft.mappings).map(([from_id, to_id]) => ({ from_id, to_id })), business_context: draft.business_context, priorities: draft.priorities }, token) : !state.plan ? api.studioPlan(jobId, token) : api.studioImplement(jobId, token)))}
          />
        </Section>
      )}

      {state.assessment && (
        <Section eyebrow="03 · Before touching anything" title="Assessment: does migrating pay off?">
          <AssessmentPanel
            assessment={state.assessment}
            stack={stack}
            planReady={!!state.plan}
            busy={busy || phase === "planning"}
            onPlan={() => void run(() => api.studioPlan(jobId, token))}
            onOpenFile={openFile}
            answers={qa}
            onAnswer={(question, answer) => setQa((current) => ({ ...current, [question]: answer }))}
            history={history}
            onReassess={reassess}
            reassessBusy={busy || phase === "assessing"}
            hasToken={hasAccess}
          />
        </Section>
      )}

      {phase === "planning" && (
        <Section eyebrow="04 · Plan" title="Bob is preparing the plan">
          <BobWork title="Bob orders the steps by dependencies" events={state.events.filter((event) => event.phase === "planning")} />
        </Section>
      )}

      {state.plan && (
        <Section eyebrow="04 · How to do it" title={`Migration plan · ${state.plan.steps.length} steps`}>
          <PlanGraph plan={state.plan} runs={runs} onOpenFile={(path) => openFile(path)} />
        </Section>
      )}

      {state.plan && (
        <Section eyebrow="05 · Do it" title="Implementation with Bob">
          <ImplementationPanel
            plan={state.plan}
            state={state}
            busy={busy}
            onImplement={() => void run(() => api.studioImplement(jobId, token))}
            onDownload={download}
            loadDiff={loadDiff}
          />
        </Section>
      )}

      {!state.assessment && phase === "idle" && stack.technologies.length === 0 && (
        <EmptyState title="No technology was recognized.">The project contains no dependency manifests and no code in the languages we know how to measure.</EmptyState>
      )}
    </div>
  );
}
