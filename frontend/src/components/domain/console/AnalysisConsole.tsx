import { useEffect, useMemo, useRef, useState } from "react";
import { Play, Square } from "lucide-react";
import { buildActivity, formatClock, STAGE_ORDER } from "../../../lib/activity";
import { isActive } from "../../../lib/flow";
import { jobLabel } from "../../../lib/format";
import { useWorkspace } from "../../../lib/workspace";
import type { StageId } from "../../../types";
import { ModeBadge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { Eyebrow } from "../../ui/Layout";
import { AnalysisStatus } from "../AnalysisStatus";
import { AgentsPanel } from "./AgentsPanel";
import { PreparingPanel, ReadyPanel, TestsPanel, ValidationPanel } from "./StagePanels";
import { STAGE_INFO, StageRail, stageStates } from "./StageRail";
import { useReplay } from "./useReplay";

const FAILURE_HINT: Record<StageId, string> = {
  preparing: "Check that the ZIP is a Python repository under 5 MB, with no symbolic links or executables.",
  auditing: "Bob did not deliver a valid dossier. Run the analysis again; if it happens again, raise BOB_MAX_COST or audit a smaller repository.",
  validating: "Bob's reply could not be validated against the code. Check bob-result.json in Reports.",
  migration: "The first cut's test sandbox failed. Check the server logs.",
  done: "The dossier could not be generated. Check the server logs.",
};

/**
 * Analysis session: what each stage does while it happens (and its replay once it has finished).
 * Everything comes from the backend events: there is no simulated progress.
 */
export function AnalysisConsole({ autoplay }: { autoplay: boolean }) {
  const { flow, activity, activityReady, go } = useWorkspace();
  const live = !!flow && isActive(flow);
  const finished = flow?.status === "done" || flow?.status === "failed";
  const replay = useReplay(activity, autoplay && finished && activityReady);
  const model = useMemo(() => buildActivity(replay.visible), [replay.visible]);
  const settled = finished && !replay.playing;
  const states = stageStates(model, settled);
  const [picked, setPicked] = useState<StageId | null>(null);
  const [clock, setClock] = useState(0);
  const panelHeading = useRef<HTMLHeadingElement>(null);
  const selectStage = (stage: StageId) => {
    setPicked(stage);
    // The content changes in the panel: focus moves there for keyboard and screen reader users.
    requestAnimationFrame(() => panelHeading.current?.focus());
  };
  const startReplay = () => {
    setPicked(null); // the replay follows the active stage (same render as the start)
    replay.start();
  };

  // Live, the clock advances even when Bob emits no events (e.g. while a subagent works).
  const createdAt = flow?.created_at;
  useEffect(() => {
    if (!live || !createdAt) return;
    const startedAt = Date.parse(createdAt);
    const tick = () => setClock(Math.max(0, (Date.now() - startedAt) / 1000));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [live, createdAt]);

  const followed = STAGE_ORDER.find((stage) => states[stage] === "running" || states[stage] === "failed")
    ?? (model.done ? "done" : [...STAGE_ORDER].reverse().find((stage) => model.stages[stage].events > 0) ?? "preparing");
  const selected = picked ?? (settled && !model.failure && model.stages.auditing.events > 0 ? "auditing" : followed);
  const now = live ? clock : replay.playhead ?? model.lastT;

  if (!flow) return null;
  if (finished && activityReady && activity.length === 0) {
    return (
      <div className="max-w-xl space-y-4">
        <AnalysisStatus flow={flow} />
        <p className="text-caption text-subtle">This analysis ran before the per-stage activity log existed.</p>
      </div>
    );
  }

  return (
    <section aria-label="Analysis session" className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-b border-line pb-4">
        <div className="min-w-0">
          <Eyebrow>Analysis session · How did IBM Bob analyze it?</Eyebrow>
          <h1 className="mt-1.5 flex flex-wrap items-center gap-3 font-display text-heading font-normal text-fg">
            {jobLabel(flow.label)}
            <ModeBadge mode={flow.execution_mode} />
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {live ? (
            <span className="flex items-center gap-2 font-mono text-caption text-fg">
              <span aria-hidden className="h-2 w-2 animate-pulse rounded-pill bg-activity" />
              En vivo · {formatClock(now)}
            </span>
          ) : replay.playing ? (
            <>
              <span className="font-mono text-caption text-fg-2 tabular-nums">{formatClock(replay.playhead ?? 0)} / {formatClock(replay.duration)}</span>
              <Button size="sm" variant="secondary" icon={<Square size={12} aria-hidden />} onClick={replay.stop}>Show the full session</Button>
            </>
          ) : activity.length > 0 ? (
            <>
              <span className="font-mono text-caption text-subtle tabular-nums">duration {formatClock(replay.duration)}</span>
              {replay.available && <Button size="sm" variant="secondary" icon={<Play size={12} aria-hidden />} onClick={startReplay}>Replay the session</Button>}
            </>
          ) : null}
        </div>
      </header>

      <div className="h-px overflow-hidden bg-line" aria-hidden>
        {live ? <div className="spectrum-rail h-full w-full" /> : replay.playing ? <div className="h-full bg-fg-2" style={{ width: `${replay.progress * 100}%` }} /> : null}
      </div>

      <div className="grid grid-cols-1 gap-6 @3xl:grid-cols-[17.5rem_minmax(0,1fr)]">
        <div className="space-y-4">
          <StageRail model={model} states={states} selected={selected} onSelect={selectStage} panelId="stage-panel" />
          {live && <p role="status" className="sr-only">Stage in progress: {STAGE_INFO[followed].running}</p>}
          {flow.status === "failed" && (
            <div role="alert" className="rounded-inner border border-danger/40 bg-danger/5 px-3 py-3">
              <p className="text-body text-fg"><span aria-hidden className="mr-1.5 text-danger">✗</span>The analysis stopped at «{STAGE_INFO[model.failure?.stage ?? "preparing"].label}»</p>
              <p className="mt-1 font-mono text-caption break-words text-fg-2">{flow.error ?? model.failure?.message}</p>
              <p className="mt-2 text-caption text-muted">{FAILURE_HINT[model.failure?.stage ?? "preparing"]}</p>
            </div>
          )}
        </div>

        <div id="stage-panel" role="region" aria-labelledby="stage-panel-title" className="min-w-0">
          <div className="mb-4">
            <h2 id="stage-panel-title" ref={panelHeading} tabIndex={-1} className="font-display text-title font-normal text-fg">{STAGE_INFO[selected].label}</h2>
            <p className="mt-0.5 text-caption text-muted">{STAGE_INFO[selected].detail}</p>
          </div>
          {selected === "preparing" && <PreparingPanel model={model} />}
          {selected === "auditing" && <AgentsPanel model={model} now={now} settled={settled} announce={live} />}
          {selected === "validating" && <ValidationPanel model={model} />}
          {selected === "migration" && <TestsPanel model={model} />}
          {selected === "done" && <ReadyPanel model={model} onOpenSummary={() => go("overview")} onOpenRisks={() => go("risks")} />}
        </div>
      </div>
    </section>
  );
}
