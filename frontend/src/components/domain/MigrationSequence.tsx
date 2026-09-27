import { plural } from "../../lib/format";
import type { MigrationResult } from "../../types";

type StepState = "passed" | "failed" | "pending";

interface Step {
  n: string;
  title: string;
  detail: string;
  files: string[];
  state: StepState;
}

const MARK: Record<StepState, { glyph: string; tone: string; label: string }> = {
  passed: { glyph: "✓", tone: "text-verified border-verified/40", label: "complete" },
  failed: { glyph: "✗", tone: "text-danger border-danger/40", label: "failed" },
  pending: { glyph: "○", tone: "text-subtle border-line", label: "not run" },
};

function testsState(result: MigrationResult, target: "legacy" | "modern"): StepState {
  const tests = result.tests.filter((test) => test.target === target);
  if (tests.every((test) => test.status === "not_run")) return "pending";  // also with no tests
  return tests.some((test) => test.status === "failed") ? "failed" : "passed";
}

/** Real sequence of the first Strangler Fig cut with its dependencies (PRODUCT.md §16). */
export function MigrationSequence({ result }: { result: MigrationResult }) {
  const legacy = testsState(result, "legacy");
  const modern = testsState(result, "modern");
  const exists = (file: string | null): StepState => (file ? "passed" : "pending");
  const legacyCount = result.tests.filter((test) => test.target === "legacy").length;
  const modernCount = result.tests.filter((test) => test.target === "modern").length;

  const first: Step = { n: "01", title: "Characterize the legacy code", detail: `${plural(legacyCount, "run", "runs")} of golden-master tests against ${result.endpoint}`, files: [result.legacy_file ?? "—"], state: legacy };
  const branches: Step[] = [
    { n: "02", title: "Implement the modern cut", detail: "Parameterized query and owner check", files: [result.modern_file ?? "—"], state: exists(result.modern_file) },
    { n: "03", title: "Strangler Fig facade", detail: "Routes only the migrated endpoint; rollback by flag", files: [result.facade_file ?? "—"], state: exists(result.facade_file) },
  ];
  const tail: Step[] = [
    { n: "04", title: "Verify parity", detail: `${plural(modernCount, "run", "runs")} of the same tests against the modern cut`, files: [], state: modern },
    { n: "05", title: "Reviewable patch", detail: "Unified diff for human review before deploying", files: [result.diff_file ?? "—"], state: exists(result.diff_file) },
  ];

  return (
    <ol className="relative space-y-3" aria-label="Migration sequence">
      <StepItem step={first} />
      <li aria-hidden className="ml-4.5 h-4 w-px bg-line-strong" />
      <li>
        <p className="mb-2 text-caption text-subtle">02 and 03 depend on 01 and can be done in parallel</p>
        <ol className="grid grid-cols-1 gap-3 @2xl:grid-cols-2">
          {branches.map((step) => <StepItem key={step.n} step={step} />)}
        </ol>
      </li>
      <li aria-hidden className="ml-4.5 h-4 w-px bg-line-strong" />
      {tail.map((step, index) => (
        <li key={step.n} className="contents">
          <StepItem step={step} bare />
          {index < tail.length - 1 && <span aria-hidden className="ml-4.5 block h-4 w-px bg-line-strong" />}
        </li>
      ))}
    </ol>
  );
}

function StepItem({ step, bare = false }: { step: Step; bare?: boolean }) {
  const mark = MARK[step.state];
  const Tag = bare ? "div" : "li";
  return (
    <Tag className="grid grid-cols-[2.25rem_1fr] gap-x-3 rounded-inner border border-line bg-surface px-3 py-3">
      <span className={`flex h-9 w-9 items-center justify-center rounded-pill border font-mono text-caption ${mark.tone}`}>
        <span aria-hidden>{step.state === "pending" ? step.n : mark.glyph}</span>
        <span className="sr-only">Step {step.n}, {mark.label}</span>
      </span>
      <div className="min-w-0">
        <p className="flex items-baseline gap-2 text-body text-fg">
          <span className="font-mono text-caption text-subtle">{step.n}</span>
          {step.title}
        </p>
        <p className="mt-0.5 text-caption text-muted">{step.detail}</p>
        {step.files.length > 0 && (
          <p className="mt-1.5 truncate font-mono text-caption text-fg-2">{step.files.join(" · ")}</p>
        )}
      </div>
    </Tag>
  );
}
