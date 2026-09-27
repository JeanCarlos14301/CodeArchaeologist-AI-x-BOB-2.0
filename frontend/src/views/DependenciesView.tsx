import { Meter, ScreenHeader, Section } from "../components/ui/Layout";
import { ErrorState, Loading } from "../components/ui/States";
import { useResource, useWorkspace } from "../lib/workspace";
import type { ArchitectureData } from "../types";
import { JobGate } from "./JobGate";

export function DependenciesView() {
  return <JobGate>{() => <Dependencies />}</JobGate>;
}

function Dependencies() {
  const architecture = useResource("architecture");
  const requirements = useResource("requirements");

  if (architecture.error) return <div className="p-6"><ErrorState title="The dependencies could not be measured." message={architecture.error} onRetry={architecture.retry} /></div>;
  if (!architecture.data) return <div className="p-6"><Loading label="Measuring dependencies…" /></div>;
  const arch = architecture.data;

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Dependencies · What does this system depend on?"
        title="Packages, modules and data"
        description="Relationships measured in the code, not a package list: who depends on whom, with how many calls and where the cycles are."
      />
      <Section eyebrow="Packages" title="Declared in requirements.txt" aside="Latest version: not checked (the analysis does not access PyPI)">
        {requirements.error ? (
          <ErrorState title="requirements.txt could not be read." message={requirements.error} onRetry={requirements.retry} />
        ) : !requirements.data ? (
          <Loading label="Reading requirements.txt…" />
        ) : requirements.data.length === 0 ? (
          <p className="text-body text-muted">The repository declares no dependencies in requirements.txt.</p>
        ) : (
          <table className="w-full max-w-3xl text-left">
            <thead><tr className="border-b border-line text-micro tracking-eyebrow text-subtle uppercase">
              <th className="py-2 font-medium">Package</th><th className="py-2 font-medium">Constraint</th><th className="py-2 font-medium">Status</th><th className="py-2 text-right font-medium">Line</th>
            </tr></thead>
            <tbody className="divide-y divide-line-subtle">
              {requirements.data.map((pkg) => (
                <tr key={`${pkg.name}-${pkg.line}`}>
                  <td className="py-2 font-mono text-body text-fg">{pkg.name}</td>
                  <td className="py-2 font-mono text-caption text-fg-2">{pkg.spec ?? "no constraint"}</td>
                  <td className="py-2 text-caption">
                    {pkg.pinned ? <span className="text-verified">✓ Pinned version</span> : <span className="text-warning">▲ Not pinned: the installation may vary</span>}
                  </td>
                  <td className="py-2 text-right font-mono text-caption text-subtle">requirements.txt:{pkg.line}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
      <ModuleDependencies arch={arch} />
      <Section eyebrow="Data" title="Persistence layer">
        <div className="grid grid-cols-1 gap-x-12 gap-y-6 @3xl:grid-cols-2">
          <div>
            <p className="text-body text-muted">Tables detected in SQL scripts</p>
            {arch.tables.length === 0 ? <p className="mt-2 text-body text-subtle">None.</p> : (
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {arch.tables.map((t) => <li key={t} className="rounded-pill border border-line px-2.5 py-0.5 font-mono text-caption text-fg">{t}</li>)}
              </ul>
            )}
          </div>
          <Meter label="Parameterized SQL queries" value={arch.sql.parameterized} max={arch.sql.total} tone="bg-verified"
            detail={arch.sql.concatenated ? `${arch.sql.concatenated} are built by concatenating text: possible SQL injection.` : "No query is built by concatenation."} />
        </div>
      </Section>
    </div>
  );
}

function ModuleDependencies({ arch }: { arch: ArchitectureData }) {
  const { go } = useWorkspace();
  const cyclePairs = new Set(arch.circular_dependencies.flatMap((cycle) => cycle.slice(0, -1).map((file, i) => `${file}>${cycle[i + 1]}`)));
  const rows = arch.modules
    .map((m) => ({
      file: m.file,
      fanIn: arch.dependencies.filter((d) => d.target === m.file).length,
      fanOut: arch.dependencies.filter((d) => d.source === m.file).length,
      deps: arch.dependencies.filter((d) => d.source === m.file),
    }))
    .filter((row) => row.fanIn + row.fanOut > 0)
    .sort((a, b) => b.fanIn + b.fanOut - (a.fanIn + a.fanOut));

  return (
    <Section eyebrow="Modules" title="Dependencies between modules" aside={arch.circular_dependencies.length ? <span className="text-danger">▲ {arch.circular_dependencies.length} cycle{arch.circular_dependencies.length === 1 ? "" : "s"}</span> : "No cycles"}>
      {arch.circular_dependencies.length > 0 && (
        <ul className="mb-4 space-y-1">
          {arch.circular_dependencies.map((cycle) => (
            <li key={cycle.join(">")} className="font-mono text-caption text-danger">↻ {cycle.join(" → ")} <span className="text-subtle">· break the cycle before extracting any of these modules</span></li>
          ))}
        </ul>
      )}
      <table className="w-full text-left">
        <thead><tr className="border-b border-line text-micro tracking-eyebrow text-subtle uppercase">
          <th className="py-2 font-medium">Module</th>
          <th className="py-2 text-right font-medium" title="Modules that call it">Fan-in</th>
          <th className="py-2 text-right font-medium" title="Modules it calls">Fan-out</th>
          <th className="py-2 pl-6 font-medium">Depends on (calls)</th>
        </tr></thead>
        <tbody className="divide-y divide-line-subtle">
          {rows.map((row) => (
            <tr key={row.file}>
              <td className="py-2"><button type="button" onClick={() => go("architecture", { file: row.file })} className="font-mono text-caption text-fg hover:text-fg-2">{row.file}</button></td>
              <td className="py-2 text-right font-mono text-caption tabular-nums">{row.fanIn}</td>
              <td className="py-2 text-right font-mono text-caption tabular-nums">{row.fanOut}</td>
              <td className="py-2 pl-6 font-mono text-caption text-fg-2">
                {row.deps.length === 0 ? <span className="text-subtle">—</span> : row.deps.map((d, i) => (
                  <span key={d.target} className={cyclePairs.has(`${d.source}>${d.target}`) ? "text-danger" : ""}>
                    {i > 0 && ", "}{d.target} <span className="text-subtle">({d.calls})</span>
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}
