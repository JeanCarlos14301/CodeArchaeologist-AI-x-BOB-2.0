import { ArrowRight } from "lucide-react";
import type { ActivityModel } from "../../../lib/activity";
import { formatCost, formatSeconds, lineRange, plural } from "../../../lib/format";
import { SEVERITY, SEVERITY_ORDER } from "../../../lib/severity";
import type { Severity } from "../../../types";
import { SeverityBadge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { Eyebrow } from "../../ui/Layout";

/** Stage 1: the ZIP's security checks and the sandbox inventory (what the repository contains). */
export function PreparingPanel({ model }: { model: ActivityModel }) {
  const inventory = model.inventory;
  const maxLanguage = Math.max(1, ...(inventory?.languages.map((item) => item.files) ?? [1]));
  return (
    <div className="space-y-6">
      <section aria-label="Security checks">
        <Eyebrow>Security checks</Eyebrow>
        {model.checks.length === 0 ? (
          <p className="mt-2 text-body text-muted">A registered team sample: it is copied from the server, with no ZIP to validate. The code never runs in this stage.</p>
        ) : (
          <ul className="mt-2 divide-y divide-line-subtle">
            {model.checks.map((check) => (
              <li key={check.name} className="grid animate-enter grid-cols-[1rem_1fr_auto] items-baseline gap-x-3 py-2">
                <span aria-hidden className="text-verified">✓</span>
                <span className="text-body text-fg-2">{check.name}</span>
                <span className="text-right font-mono text-caption text-fg">
                  {check.value} <span className="text-subtle">{check.limit}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {!inventory ? (
        <p className="text-caption text-subtle">Copying the repository into the sandbox…</p>
      ) : (
        <section aria-label="Repository inventory" className="space-y-5">
          <dl className="grid grid-cols-3 gap-x-6">
            {[
              ["Files", inventory.files.toLocaleString("en")],
              ["Python lines", inventory.python_lines.toLocaleString("en")],
              ["Size", `${(inventory.bytes / 1024).toFixed(0)} KB`],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-micro tracking-eyebrow text-subtle uppercase">{label}</dt>
                <dd className="mt-1 font-display text-heading text-fg tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
          <div>
            <Eyebrow>Languages by file</Eyebrow>
            <ul className="mt-2 space-y-1.5">
              {inventory.languages.map((language) => (
                <li key={language.name} className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-3 text-caption">
                  <span className="text-fg-2">{language.name}</span>
                  <span className="h-1 overflow-hidden rounded-pill bg-raised">
                    <span className="block h-full rounded-pill bg-fg-2" style={{ width: `${(language.files / maxLanguage) * 100}%` }} />
                  </span>
                  <span className="text-right font-mono text-fg tabular-nums">{language.files}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid grid-cols-1 gap-5 @2xl:grid-cols-2">
            <div>
              <Eyebrow>Main folders</Eyebrow>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {inventory.top_dirs.map((dir) => (
                  <li key={dir.name} className="rounded-pill border border-line px-2.5 py-0.5 font-mono text-caption text-fg-2">
                    {dir.name} <span className="text-subtle">{dir.files}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <Eyebrow>Outside the sandbox</Eyebrow>
              <p className="mt-2 font-mono text-caption text-subtle">{inventory.excluded.join(" · ")}</p>
            </div>
          </div>
          <p className="font-mono text-caption text-subtle">sha256 {inventory.sha256}</p>
        </section>
      )}
    </div>
  );
}

/** Stage 3: every Bob citation checked against the code (file, lines, snippet). */
export function ValidationPanel({ model }: { model: ActivityModel }) {
  const { checks, summary } = model.evidence;
  const valid = checks.filter((check) => check.status === "valid").length;
  const invalid = checks.length - valid;
  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 @2xl:grid-cols-4">
        {[
          ["Citations verified", <span key="v" className="text-verified">✓ {valid}</span>],
          ["Do not match", <span key="i" className={invalid ? "text-danger" : "text-subtle"}>✗ {invalid}</span>],
          ["Findings accepted", summary ? summary.accepted : "…"],
          ["Discarded", summary ? summary.rejected : "…"],
        ].map(([label, value]) => (
          <div key={String(label)}>
            <dt className="text-micro tracking-eyebrow text-subtle uppercase">{label}</dt>
            <dd className="mt-1 font-mono text-body text-fg tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      {checks.length === 0 ? (
        <p className="text-body text-muted">Waiting for Bob's citations…</p>
      ) : (
        <ul aria-label="Checked citations" className="grid grid-cols-1 gap-x-6 @3xl:grid-cols-2">
          {checks.map((check) => (
            <li key={check.seq} className="grid animate-enter grid-cols-[1rem_2.75rem_1fr] items-baseline gap-x-2 border-b border-line-subtle py-2 text-caption">
              <span aria-hidden className={check.status === "valid" ? "text-verified" : "text-danger"}>{check.status === "valid" ? "✓" : "✗"}</span>
              <span className={`font-mono ${check.severity ? SEVERITY[check.severity as Severity].text : "text-subtle"}`}>{check.findingId}</span>
              <span className="min-w-0">
                <span className="block truncate font-mono text-fg">{check.path}{check.lineStart ? `:${lineRange(check.lineStart, check.lineEnd ?? check.lineStart)}` : ""}</span>
                <span className="block truncate text-subtle">{check.reason}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {summary && (
        <p className="text-caption text-subtle">
          With the accepted evidence, Python computed the risk of {plural(summary.riskScored, "finding", "findings")}
          {summary.pertDays != null && <> and the first cut's PERT estimate (<span className="font-mono text-fg-2">{summary.pertDays.toFixed(1)} days</span>)</>}.
        </p>
      )}
    </div>
  );
}

/** Stage 4: the first cut's characterization tests, or why they do not run. */
export function TestsPanel({ model }: { model: ActivityModel }) {
  const { tests, skipped, summary } = model.migration;
  if (skipped) {
    return (
      <div className="rounded-panel border border-dashed border-line-strong px-5 py-5">
        <p className="text-body text-fg">No first cut was run</p>
        <p className="mt-1 text-body text-muted">{skipped} The tested cut exists for the team's registered samples.</p>
      </div>
    );
  }
  if (tests.length === 0) return <p className="text-body text-muted">Preparing the test sandbox…</p>;
  return (
    <div className="space-y-5">
      {(["legacy", "modern"] as const).map((target) => {
        const group = tests.filter((test) => test.target === target);
        if (group.length === 0) return null;
        return (
          <section key={target} aria-label={target === "legacy" ? "Against the legacy code" : "Against the modern cut"}>
            <Eyebrow>{target === "legacy" ? "Against the legacy code" : "Against the modern cut"}</Eyebrow>
            <ul className="mt-2 divide-y divide-line-subtle">
              {group.map((test) => (
                <li key={test.seq} className="grid animate-enter grid-cols-[1rem_1fr_auto] items-baseline gap-x-3 py-2 text-caption">
                  <span aria-hidden className={test.status === "passed" ? "text-verified" : test.status === "failed" ? "text-danger" : "text-subtle"}>
                    {test.status === "passed" ? "✓" : test.status === "failed" ? "✗" : "○"}
                  </span>
                  <span className="truncate font-mono text-fg-2">{test.name}{test.reason && <span className="block text-danger">{test.reason}</span>}</span>
                  <span className="font-mono text-subtle tabular-nums">{Math.round(test.durationMs)} ms</span>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {summary && (
        <p className={`text-body ${summary.status === "passed" ? "text-verified" : "text-danger"}`}>
          {summary.status === "passed" ? "✓ Same observable behavior in legacy and modern" : "✗ The modern cut does not reproduce the behavior"} · <span className="font-mono">{summary.endpoint}</span>
        </p>
      )}
    </div>
  );
}

/** Stage 5: the dossier and the next step. */
export function ReadyPanel({ model, onOpenSummary, onOpenRisks }: { model: ActivityModel; onOpenSummary: () => void; onOpenRisks: () => void }) {
  const done = model.done;
  if (!done) return <p className="text-body text-muted">The dossier will appear when validation finishes.</p>;
  return (
    <div className="space-y-5">
      <p className="font-display text-heading text-fg">{plural(done.findings, "finding", "findings")} with verified evidence</p>
      <ul className="flex flex-wrap gap-x-6 gap-y-2">
        {SEVERITY_ORDER.filter((severity) => done.bySeverity[severity]).map((severity) => (
          <li key={severity} className="flex items-center gap-2">
            <SeverityBadge severity={severity} />
            <span className="font-mono text-body text-fg tabular-nums">{done.bySeverity[severity]}</span>
          </li>
        ))}
      </ul>
      <p className="font-mono text-caption text-subtle">
        {done.evidenceValid}/{done.evidenceTotal} citations verified · IBM Bob {formatCost(done.cost)} · {formatSeconds(done.durationMs)}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button onClick={onOpenRisks} icon={<ArrowRight size={14} aria-hidden />}>Review the {done.findings} risks</Button>
        <Button variant="ghost" onClick={onOpenSummary}>Open the system overview</Button>
      </div>
    </div>
  );
}
