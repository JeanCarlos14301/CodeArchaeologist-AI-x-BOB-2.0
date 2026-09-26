import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "../api";
import { AssessmentPanel } from "../components/domain/studio/AssessmentPanel";
import { BobWork } from "../components/domain/studio/BobWork";
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
  { id: "targets", label: "Destinos" },
  { id: "assessment", label: "Evaluación" },
  { id: "plan", label: "Plan" },
  { id: "implementation", label: "Implementación" },
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

/** Estudio de modernización: medir el stack, decidir destinos, entender el impacto, planificar e implementar con Bob. */
export function StudioView() {
  const { flow, token, setToken, go, offline } = useWorkspace();
  const jobId = flow?.id ?? "";
  const [stack, setStack] = useState<StackReport | null>(null);
  const [stackError, setStackError] = useState<string | null>(null);
  const [state, setState] = useState<StudioState | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const seeded = useRef<string | null>(null);

  const refresh = useCallback(() => api.studio(jobId, token).then(setState).catch((err: Error) => setActionError(err.message)), [jobId, token]);

  useEffect(() => {
    setStack(null);
    setStackError(null);
    api.stack(jobId, token).then(setStack).catch((err: Error) => setStackError(err.message));
    void refresh();
  }, [jobId, token, refresh]);

  // Al abrir un análisis con decisiones previas, se recuperan en el tablero.
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
      setActionError(err instanceof ApiError && err.status === 403 ? "El token no es válido." : (err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const assess = () => {
    const request: AssessRequest = {
      mode: draft.mode,
      mappings: draft.mode === "chosen" ? Object.entries(draft.mappings).map(([from_id, to_id]) => ({ from_id, to_id })) : [],
      business_context: draft.business_context.trim(),
      priorities: draft.priorities,
    };
    void run(() => api.studioAssess(jobId, request, token));
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

  if (offline) return <ErrorState title="No hay conexión con el backend." message="GET /api/audits no respondió." hint="Arranca el servidor y recarga la página." />;
  if (stackError) return <ErrorState title="No se pudo medir el stack." message={stackError} hint="El código de este análisis puede haber sido eliminado del servidor." onRetry={() => setToken(token)} />;
  if (!stack || !state) return <Loading label="Midiendo el stack del proyecto…" />;

  const phase = state.phase;
  const hasAssessment = !!state.assessment;
  const editable = !working;

  return (
    <div>
      <ol className="mb-2 flex flex-wrap gap-x-6 gap-y-2 border-b border-line pb-4" aria-label="Progreso del estudio">
        {STEPS.map((step, index) => {
          const status = stepStatus(state, step.id);
          const tone = status === "done" ? "text-verified" : status === "failed" ? "text-danger" : status === "active" ? "text-fg" : "text-subtle";
          return (
            <li key={step.id} aria-current={status === "active" ? "step" : undefined} className={`flex items-center gap-2 text-caption ${tone}`}>
              <span aria-hidden className="font-mono">{status === "done" ? "✓" : status === "failed" ? "✗" : status === "active" ? "●" : String(index + 1).padStart(2, "0")}</span>
              {step.label}
              <span className="sr-only">{status === "done" ? ", completado" : status === "failed" ? ", falló" : status === "active" ? ", en curso" : ", pendiente"}</span>
            </li>
          );
        })}
      </ol>

      <Section eyebrow="01 · Lo que usas hoy" title="Stack detectado en tu proyecto">
        <StackBoard stack={stack} />
      </Section>

      <Section eyebrow="02 · A dónde quieres ir" title="Destinos de la migración">
        <fieldset disabled={!editable} className="min-w-0 border-0 p-0">
          <TransformBoard
            stack={stack}
            draft={draft}
            onChange={setDraft}
            onSubmit={assess}
            busy={busy || phase === "assessing"}
            needsToken={!token}
            token={token}
            onToken={setToken}
            resetsWork={hasAssessment}
          />
        </fieldset>
        {actionError && <div className="mt-4"><ErrorState title="La acción no se completó." message={actionError} onRetry={() => setActionError(null)} retryLabel="Descartar" /></div>}
      </Section>

      {phase === "assessing" && (
        <Section eyebrow="03 · Evaluación" title="Bob está evaluando">
          <BobWork title="Bob lee tu código y pesa qué se gana y qué se sacrifica" events={state.events.filter((event) => event.phase === "assessing")} />
        </Section>
      )}
      {phase === "failed" && state.error && (
        <Section eyebrow="Algo salió mal" title="La última operación con Bob falló">
          <ErrorState
            title="Bob no pudo completar el paso."
            message={state.error}
            hint="No se gastó trabajo en vano: lo ya generado sigue disponible. Puedes reintentar."
            onRetry={() => void run(() => (!state.assessment ? api.studioAssess(jobId, { mode: draft.mode, mappings: Object.entries(draft.mappings).map(([from_id, to_id]) => ({ from_id, to_id })), business_context: draft.business_context, priorities: draft.priorities }, token) : !state.plan ? api.studioPlan(jobId, token) : api.studioImplement(jobId, token)))}
          />
        </Section>
      )}

      {state.assessment && (
        <Section eyebrow="03 · Antes de tocar nada" title="Evaluación: ¿conviene migrar?">
          <AssessmentPanel
            assessment={state.assessment}
            stack={stack}
            planReady={!!state.plan}
            busy={busy || phase === "planning"}
            onPlan={() => void run(() => api.studioPlan(jobId, token))}
            onOpenFile={openFile}
          />
        </Section>
      )}

      {phase === "planning" && (
        <Section eyebrow="04 · Plan" title="Bob está preparando el plan">
          <BobWork title="Bob ordena los pasos por dependencias" events={state.events.filter((event) => event.phase === "planning")} />
        </Section>
      )}

      {state.plan && (
        <Section eyebrow="04 · Cómo hacerlo" title={`Plan de migración · ${state.plan.steps.length} pasos`}>
          <PlanGraph plan={state.plan} runs={runs} onOpenFile={(path) => openFile(path)} />
        </Section>
      )}

      {state.plan && (
        <Section eyebrow="05 · Hacerlo" title="Implementación con Bob">
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
        <EmptyState title="No se reconoció ninguna tecnología.">El proyecto no contiene manifiestos de dependencias ni código en los lenguajes que sabemos medir.</EmptyState>
      )}
    </div>
  );
}
