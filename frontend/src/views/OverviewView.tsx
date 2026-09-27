import { ArrowRight } from "lucide-react";
import { PertRange } from "../components/domain/PertRange";
import { ModeBadge, SeverityBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataList, Meter, ScreenHeader, Section } from "../components/ui/Layout";
import { formatCost, formatDate, formatPercent, formatSeconds, lineRange } from "../lib/format";
import { bySeverity, countBySeverity } from "../lib/severity";
import { detectStack } from "../lib/stack";
import { useResource, useWorkspace } from "../lib/workspace";
import type { Dossier } from "../types";
import { JobGate } from "./JobGate";

export function OverviewView() {
  return <JobGate>{(dossier) => <Overview dossier={dossier} />}</JobGate>;
}

function Overview({ dossier }: { dossier: Dossier }) {
  const { go } = useWorkspace();
  const architecture = useResource("architecture");
  const requirements = useResource("requirements");
  const arch = architecture.data;
  const stack = detectStack(arch, requirements.data ?? []);
  const counts = countBySeverity(dossier.findings);
  const top = [...dossier.findings].sort(bySeverity).slice(0, 5);
  const tests = dossier.migration?.tests ?? [];
  const passed = (target: "legacy" | "modern") => tests.filter((t) => t.target === target && t.status === "passed").length;
  const total = (target: "legacy" | "modern") => tests.filter((t) => t.target === target).length;
  const stackLine = [stack.language, ...stack.frameworks, stack.data].filter(Boolean).join(" · ");

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Overview · What kind of system is it?"
        title={dossier.repo_name}
        description={stackLine ? `${stackLine}${arch ? ` · ${arch.totals.files} Python files · ${arch.totals.functions} functions · ${arch.routes.length} HTTP routes` : ""}` : "Detecting the stack…"}
        meta={<>
          <ModeBadge mode={dossier.execution_mode} />
          <span>Generated {formatDate(dossier.generated_at)}</span>
          <span>Stack detected from the repository's own requirements.txt, AST and SQL</span>
        </>}
        actions={<Button variant="secondary" onClick={() => go("risks")} icon={<ArrowRight size={14} aria-hidden />}>Review {dossier.findings.length} risks</Button>}
      />

      <div className="grid grid-cols-1 gap-x-12 @3xl:grid-cols-2">
        <Section eyebrow="Health" title="What the analysis found">
          <DataList rows={[
            { label: "Findings with verified evidence", value: `${dossier.stats.findings_validated}/${dossier.stats.findings_reported}`, hint: dossier.rejected_findings.length ? `${dossier.rejected_findings.length} discarded by the validator` : "none discarded" },
            { label: <SeverityBadge severity="critical" />, value: counts.critical },
            { label: <SeverityBadge severity="high" />, value: counts.high },
            { label: <SeverityBadge severity="medium" />, value: counts.medium },
            { label: <SeverityBadge severity="low" />, value: counts.low },
            { label: "Circular dependencies", value: arch ? arch.circular_dependencies.length : "…" },
            { label: "SQL built by concatenation", value: arch ? `${arch.sql.concatenated} of ${arch.sql.total}` : "…" },
          ]} />
        </Section>

        <Section eyebrow="Readiness" title="How ready it is to modernize">
          <div className="space-y-5">
            <Meter label="Evidence verified by code" value={dossier.stats.evidence_valid} max={dossier.stats.evidence_total} tone="bg-verified"
              detail={`${formatPercent(dossier.stats.evidence_valid_ratio)} of Bob's citations exist in the repository.`} />
            {arch && <Meter label="Parameterized SQL queries" value={arch.sql.parameterized} max={arch.sql.total} tone="bg-fg"
              detail={arch.sql.total ? "The rest is built by concatenating text." : "No SQL queries were detected."} />}
            <Meter label="Characterization tests · legacy" value={passed("legacy")} max={total("legacy")} tone="bg-verified"
              detail={total("legacy") ? "They pin the current behavior of the first cut's endpoint." : "Not run: uploaded code never runs."} />
            <Meter label="Characterization tests · modern" value={passed("modern")} max={total("modern")} tone="bg-verified" />
          </div>
        </Section>
      </div>

      <Section eyebrow="Top risks" title="What can complicate the migration the most" aside={<button type="button" className="text-caption text-fg-2 hover:text-fg" onClick={() => go("risks")}>View all {dossier.findings.length} →</button>}>
        <ul className="divide-y divide-line-subtle border-y border-line-subtle">
          {top.map((finding) => (
            <li key={finding.id}>
              <button type="button" onClick={() => go("risks", { finding: finding.id })} className="grid w-full grid-cols-[7rem_1fr_auto] items-baseline gap-4 py-3 text-left hover:bg-raised">
                <SeverityBadge severity={finding.severity} />
                <span className="text-body text-fg">{finding.title}</span>
                <span className="hidden font-mono text-caption text-subtle md:inline">{finding.evidence[0].path}:{lineRange(finding.evidence[0].line_start, finding.evidence[0].line_end)}</span>
              </button>
            </li>
          ))}
        </ul>
      </Section>

      <div className="grid grid-cols-1 gap-x-12 @3xl:grid-cols-2">
        <Section eyebrow="First cut" title={dossier.recommendation?.recommended
          ? `Migrate ${dossier.recommendation.recommended.endpoint} first`
          : dossier.migration && dossier.migration.status !== "not_run" ? `Migrate ${dossier.migration.endpoint}` : "First cut estimate"}>
          {dossier.first_cut_pert ? (
            <>
              <PertRange pert={dossier.first_cut_pert} />
              <Button size="sm" variant="secondary" className="mt-5" onClick={() => go("modernization")}>View the modernization plan</Button>
            </>
          ) : (
            <p className="text-body text-muted">There is no PERT estimate for this analysis.</p>
          )}
        </Section>

        <Section eyebrow="Traceability" title="Where these figures come from">
          <DataList rows={[
            { label: "Analysis", value: dossier.job_id ?? "—" },
            { label: "Code SHA-256", value: <span title={dossier.source_sha256 ?? ""}>{dossier.source_sha256 ? `${dossier.source_sha256.slice(0, 16)}…` : "—"}</span> },
            { label: "IBM Bob task", value: dossier.bob_task_id ? `${dossier.bob_task_id.slice(0, 12)}…` : "—" },
            { label: "Bob cost · duration", value: `${formatCost(dossier.stats.bob_cost)} · ${formatSeconds(dossier.stats.bob_duration_ms)}` },
            { label: "Contract", value: `schema v${dossier.schema_version}` },
          ]} />
          <p className="mt-3 text-caption text-subtle">The Python pipeline computes the figures; Bob only contributes findings, and each one is verified.</p>
        </Section>
      </div>
    </div>
  );
}
