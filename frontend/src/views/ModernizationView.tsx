import { useState } from "react";
import { MessageSquareText } from "lucide-react";
import { CodeViewer, toLines } from "../components/domain/CodeViewer";
import { MigrationOptions } from "../components/domain/MigrationOptions";
import { MigrationRecommendationView } from "../components/domain/MigrationRecommendation";
import { MigrationSequence } from "../components/domain/MigrationSequence";
import { PertRange } from "../components/domain/PertRange";
import { Button } from "../components/ui/Button";
import { Eyebrow, Meter, ScreenHeader, Section, Segmented } from "../components/ui/Layout";
import { EmptyState, ErrorState, Loading } from "../components/ui/States";
import { importedFramework } from "../lib/stack";
import { useResource, useWorkspace } from "../lib/workspace";
import type { Dossier, MigrationViewData } from "../types";
import { StudioGate } from "./JobGate";
import { StudioView } from "./StudioView";

type Tab = "studio" | "cut";

export function ModernizationView() {
  return <StudioGate>{() => <ModernizationTabs />}</StudioGate>;
}

/** The Studio (any project) and, if there was an audit, the first cut and the options that came from it. */
function ModernizationTabs() {
  const { dossier } = useWorkspace();
  // An audit with a route ranking opens on its recommendation; projects without one open the Studio.
  const [tab, setTab] = useState<Tab>(() => (dossier?.recommendation?.recommended ? "cut" : "studio"));
  if (dossier && tab === "cut") {
    return (
      <>
        <div className="px-6 pt-5 @3xl:px-10"><TabSwitch tab={tab} onChange={setTab} /></div>
        <Modernization dossier={dossier} />
      </>
    );
  }
  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Modernization · How do I migrate safely?"
        title="Modernization Studio"
        description="Measure which technologies your project uses, choose where to migrate (or let Bob recommend it), understand what is gained and what is traded away, and ask Bob for a plan and its implementation."
        actions={dossier ? <TabSwitch tab={tab} onChange={setTab} /> : undefined}
      />
      <StudioView />
    </div>
  );
}

function TabSwitch({ tab, onChange }: { tab: Tab; onChange: (tab: Tab) => void }) {
  return (
    <Segmented<Tab>
      label="Modernization view"
      value={tab}
      onChange={onChange}
      options={[{ value: "studio", label: "Studio" }, { value: "cut", label: "Recommendation and first cut" }]}
    />
  );
}

function Modernization({ dossier }: { dossier: Dossier }) {
  const { seedComposer, go } = useWorkspace();
  const options = dossier.migration_options ?? [];
  const recommended = dossier.recommendation?.recommended ?? null;
  // Only a cut that really ran (passed or failed) has code and tests to show.
  const hasMigration = !!dossier.migration && dossier.migration.status !== "not_run";
  const title = hasMigration && dossier.migration
    ? `First cut tested: ${dossier.migration.endpoint}`
    : recommended ? `Recommended cut: ${recommended.endpoint}` : "Modernization plan";

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Modernization · How do I migrate safely?"
        title={title}
        description="Strangler Fig: one endpoint at a time is extracted behind a facade, with tests that pin the legacy behavior and must pass the same way on the new code."
        actions={<Button icon={<MessageSquareText size={14} aria-hidden />} onClick={() => seedComposer("What should I migrate after the first cut, and in what order? Justify it with the code.")}>Ask Bob for the next cut</Button>}
      />
      <Section eyebrow="Recommendation" title="What to migrate first">
        {dossier.recommendation && recommended ? (
          <MigrationRecommendationView recommendation={dossier.recommendation} findings={dossier.findings} onOpenFinding={(id) => go("risks", { finding: id })} />
        ) : (
          <EmptyState title="No candidate Flask routes were detected.">
            The migration ranking scores every route in the code; without routes there is no first cut by endpoint to recommend.
          </EmptyState>
        )}
      </Section>
      <Section eyebrow="Options" title="Bob's qualitative reading">
        {options.length > 0 ? (
          <>
            <MigrationOptions options={options} findings={dossier.findings} onOpenFinding={(id) => go("risks", { finding: id })} />
            <p className="mt-3 text-caption text-subtle">
              Bob writes one option per route in the ranking. Code checked that it describes real routes from the ranking, that the
              recommended one is the cut the engine picked and that it carries no figures: days and risk come from the code, not from Bob.
            </p>
          </>
        ) : (
          <EmptyState title="This analysis does not include Bob's reading.">
            Bob writes it only in live analyses, and it is discarded if it describes routes that are not in the ranking, recommends another cut
            or carries figures. Imported analyses do not consult it.
          </EmptyState>
        )}
      </Section>
      {hasMigration ? <MigrationDetail /> : (
        <Section>
          <EmptyState title="This analysis does not include a tested first cut.">
            For security, uploaded code never runs, so no characterization tests are run on it.
            The tested cut exists for the registered samples; below is the effort estimate if the pipeline computed it.
          </EmptyState>
        </Section>
      )}
      {dossier.first_cut_pert && (
        <Section eyebrow="Effort" title={recommended ? "PERT estimate of the recommended cut" : "PERT estimate of the first cut"}>
          <div className="grid grid-cols-1 gap-x-12 gap-y-6 @4xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <PertRange pert={dossier.first_cut_pert} />
            <div>
              <Eyebrow>Measured on the code</Eyebrow>
              <p className="mt-1.5 font-mono text-caption text-fg-2">
                {dossier.first_cut_pert.affected_routes} routes · {dossier.first_cut_pert.affected_functions} functions · {dossier.first_cut_pert.affected_lines} lines · complexity {dossier.first_cut_pert.affected_complexity}
              </p>
              <Eyebrow className="mt-4">Assumptions</Eyebrow>
              <ul className="mt-1.5 list-disc space-y-1 pl-4 text-caption text-muted">
                {dossier.first_cut_pert.assumptions.map((a) => <li key={a}>{a}</li>)}
              </ul>
            </div>
          </div>
        </Section>
      )}
    </div>
  );
}

function MigrationDetail() {
  const migration = useResource("migration");
  if (migration.error) return <Section><ErrorState title="The first cut could not be loaded." message={migration.error} onRetry={migration.retry} /></Section>;
  if (!migration.data) return <Section><Loading label="Loading the first cut…" /></Section>;
  const data = migration.data;
  const result = data.result;
  const legacy = importedFramework(data.legacy_code);
  const modern = importedFramework(data.modern_code);
  const count = (target: "legacy" | "modern", status: string) => result.tests.filter((t) => t.target === target && t.status === status).length;
  const total = (target: "legacy" | "modern") => result.tests.filter((t) => t.target === target).length;

  return (
    <>
      <Section eyebrow="Transformation" title="Current → target">
        <div className="grid grid-cols-1 items-stretch gap-3 @2xl:grid-cols-[1fr_auto_1fr]">
          <Endpoint tag="CURRENT" framework={legacy} file={result.legacy_file} note="Legacy monolith, still serving the other routes" />
          <div className="flex items-center justify-center font-mono text-caption text-subtle" aria-hidden>→ facade →</div>
          <Endpoint tag="TARGET" framework={modern} file={result.modern_file} note={result.implementation_origin} />
        </div>
        <p className="mt-3 text-caption text-subtle">Framework detected in each file's imports · facade: <span className="font-mono text-fg-2">{result.facade_file ?? "—"}</span></p>
      </Section>
      <div className="grid grid-cols-1 gap-x-12 @4xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Section eyebrow="Sequence" title="Steps and dependencies">
          <MigrationSequence result={result} />
        </Section>
        <Section eyebrow="Validation" title="Characterization tests">
          <div className="space-y-5">
            <Meter label="Against the legacy code" value={count("legacy", "passed")} max={total("legacy")} tone="bg-verified" />
            <Meter label="Against the modern cut" value={count("modern", "passed")} max={total("modern")} tone="bg-verified" />
          </div>
          <ul className="mt-5 divide-y divide-line-subtle border-t border-line-subtle">
            {result.tests.map((test, i) => (
              <li key={`${test.target}-${test.name}-${i}`} className="grid grid-cols-[4.5rem_1fr_auto] items-baseline gap-3 py-2 text-caption">
                <span className="font-mono text-subtle">{test.target === "legacy" ? "legado" : "moderno"}</span>
                <span className="truncate font-mono text-fg-2" title={test.name}>{test.name}{test.reason && <span className="block text-danger">{test.reason}</span>}</span>
                <span className={test.status === "passed" ? "text-verified" : test.status === "failed" ? "text-danger" : "text-subtle"}>
                  {test.status === "passed" ? "✓ passed" : test.status === "failed" ? "✗ failed" : "○ not run"} <span className="font-mono text-subtle tabular-nums">{Math.round(test.duration_ms)} ms</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-caption text-subtle">Passing tests do not prove the change is safe: they confirm the endpoint's observed behavior is the same.</p>
        </Section>
      </div>
      <CodeComparison data={data} />
    </>
  );
}

function Endpoint({ tag, framework, file, note }: { tag: string; framework: string | null; file: string | null; note: string }) {
  return (
    <div className="rounded-panel border border-line bg-surface px-4 py-3">
      <Eyebrow>{tag}</Eyebrow>
      <p className="mt-1 font-display text-title text-fg">{framework ?? "Framework not detected"}</p>
      <p className="mt-0.5 font-mono text-caption text-fg-2">{file ?? "—"}</p>
      <p className="mt-1.5 text-caption text-subtle">{note}</p>
    </div>
  );
}

type CodeTab = "legacy" | "modern" | "facade";

function CodeComparison({ data }: { data: MigrationViewData }) {
  const [tab, setTab] = useState<CodeTab>("modern");
  const code = { legacy: data.legacy_code, modern: data.modern_code, facade: data.facade_code }[tab];
  const file = { legacy: data.result.legacy_file, modern: data.result.modern_file, facade: data.result.facade_file }[tab];
  return (
    <Section eyebrow="Code" title="Legacy, modern cut and facade" aside={
      <Segmented<CodeTab> label="File" value={tab} onChange={setTab} options={[
        { value: "legacy", label: "Legacy", disabled: !data.legacy_code },
        { value: "modern", label: "Modern", disabled: !data.modern_code },
        { value: "facade", label: "Facade", disabled: !data.facade_code },
      ]} />
    }>
      {code ? <CodeViewer path={file ?? tab} lines={toLines(code)} maxHeight="32rem" caption={`${code.split("\n").length} lines`} /> : <p className="text-body text-muted">File not available.</p>}
    </Section>
  );
}
