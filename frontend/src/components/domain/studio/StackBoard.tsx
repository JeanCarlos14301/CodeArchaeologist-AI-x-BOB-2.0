import { Eyebrow } from "../../ui/Layout";
import { cleanVersion } from "../../../lib/format";
import { TechIcon } from "./TechIcon";
import type { DetectedTech, StackReport } from "../../../types";

const KINDS: { kind: string; label: string }[] = [
  { kind: "language", label: "Languages" },
  { kind: "backend", label: "Backend" },
  { kind: "frontend", label: "Frontend" },
  { kind: "database", label: "Data" },
  { kind: "orm", label: "Data access" },
  { kind: "infra", label: "Infrastructure" },
  { kind: "testing", label: "Testing" },
  { kind: "build", label: "Build" },
];

const ARCHITECTURE: Record<StackReport["architecture"]["kind"], { label: string; note: string }> = {
  monolith: { label: "Monolith", note: "A single deployable application." },
  "multi-app": { label: "Several applications", note: "Backend and frontend as separate applications." },
  microservices: { label: "Microservices", note: "Several services with their own code." },
  unknown: { label: "Undetermined", note: "No application framework was found." },
};

function evidenceTitle(tech: DetectedTech): string {
  const lines = tech.evidence.filter((item) => item.path).map((item) => (item.line ? `${item.path}:${item.line}` : item.path));
  return lines.length ? `Detected in ${lines.join(", ")}` : "Detected by file extension";
}

/** What the project uses today, measured on the code: each technology with its evidence in the tooltip. */
export function StackBoard({ stack }: { stack: StackReport }) {
  const architecture = ARCHITECTURE[stack.architecture.kind];
  const languageShare = new Map(stack.languages.map((language) => [language.id, language.share]));
  const multiService = stack.services.length > 1;

  return (
    <div>
      <div className="grid grid-cols-1 gap-x-10 gap-y-3 @3xl:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
        <div>
          <Eyebrow>Detected architecture</Eyebrow>
          <p className="mt-1 font-display text-title text-fg">{architecture.label}</p>
          <p className="text-caption text-subtle">{architecture.note}</p>
        </div>
        <ul className="space-y-1 text-caption text-muted">
          {stack.architecture.basis.map((line) => (
            <li key={line} className="grid grid-cols-[1rem_1fr]"><span aria-hidden className="text-subtle">·</span><span>{line}</span></li>
          ))}
          <li className="grid grid-cols-[1rem_1fr] text-subtle"><span aria-hidden>·</span><span className="font-mono">{stack.totals.files} files · {stack.totals.lines} lines of code · {stack.totals.technologies} technologies</span></li>
        </ul>
      </div>

      <div className="mt-5 border-b border-line-subtle">
        {KINDS.map(({ kind, label }) => {
          const items = stack.technologies.filter((tech) => tech.kind === kind);
          if (!items.length) return null;
          return (
            <div key={kind} className="grid grid-cols-1 gap-x-6 gap-y-2 border-t border-line-subtle py-3 @2xl:grid-cols-[8.5rem_minmax(0,1fr)]">
              <Eyebrow className="pt-1.5">{label}</Eyebrow>
              <ul className="flex flex-wrap gap-2">
                {items.map((tech) => (
                  <li key={`${tech.id}-${tech.service}`} title={evidenceTitle(tech)} className="inline-flex h-8 items-center gap-2 rounded-pill border border-line pr-3 pl-2.5 text-caption text-fg">
                    <TechIcon slug={tech.icon} name={tech.name} size={16} />
                    <span>{tech.name}</span>
                    {kind === "language" && languageShare.has(tech.id) && <span className="font-mono text-subtle tabular-nums">{Math.round((languageShare.get(tech.id) ?? 0) * 100)}%</span>}
                    {tech.version && <span className="font-mono text-subtle">{cleanVersion(tech.version)}</span>}
                    {multiService && tech.service && tech.service !== "." && <span className="font-mono text-subtle">· {tech.service}</span>}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
