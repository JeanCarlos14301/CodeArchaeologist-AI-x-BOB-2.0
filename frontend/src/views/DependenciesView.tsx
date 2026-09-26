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

  if (architecture.error) return <div className="p-6"><ErrorState title="No se pudieron medir las dependencias." message={architecture.error} onRetry={architecture.retry} /></div>;
  if (!architecture.data) return <div className="p-6"><Loading label="Midiendo dependencias…" /></div>;
  const arch = architecture.data;

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader
        eyebrow="Dependencias · ¿De qué depende este sistema?"
        title="Paquetes, módulos y datos"
        description="Relaciones medidas en el código, no una lista de paquetes: quién depende de quién, con cuántas llamadas y dónde hay ciclos."
      />
      <Section eyebrow="Paquetes" title="Declarados en requirements.txt" aside="Versión más reciente: no consultada (el análisis no accede a PyPI)">
        {requirements.error ? (
          <ErrorState title="No se pudo leer requirements.txt." message={requirements.error} onRetry={requirements.retry} />
        ) : !requirements.data ? (
          <Loading label="Leyendo requirements.txt…" />
        ) : requirements.data.length === 0 ? (
          <p className="text-body text-muted">El repositorio no declara dependencias en requirements.txt.</p>
        ) : (
          <table className="w-full max-w-3xl text-left">
            <thead><tr className="border-b border-line text-micro tracking-eyebrow text-subtle uppercase">
              <th className="py-2 font-medium">Paquete</th><th className="py-2 font-medium">Restricción</th><th className="py-2 font-medium">Estado</th><th className="py-2 text-right font-medium">Línea</th>
            </tr></thead>
            <tbody className="divide-y divide-line-subtle">
              {requirements.data.map((pkg) => (
                <tr key={`${pkg.name}-${pkg.line}`}>
                  <td className="py-2 font-mono text-body text-fg">{pkg.name}</td>
                  <td className="py-2 font-mono text-caption text-fg-2">{pkg.spec ?? "sin restricción"}</td>
                  <td className="py-2 text-caption">
                    {pkg.pinned ? <span className="text-verified">✓ Versión fijada</span> : <span className="text-warning">▲ Sin fijar: la instalación puede variar</span>}
                  </td>
                  <td className="py-2 text-right font-mono text-caption text-subtle">requirements.txt:{pkg.line}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
      <ModuleDependencies arch={arch} />
      <Section eyebrow="Datos" title="Capa de persistencia">
        <div className="grid gap-x-12 gap-y-6 @3xl:grid-cols-2">
          <div>
            <p className="text-body text-muted">Tablas detectadas en scripts SQL</p>
            {arch.tables.length === 0 ? <p className="mt-2 text-body text-subtle">Ninguna.</p> : (
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {arch.tables.map((t) => <li key={t} className="rounded-pill border border-line px-2.5 py-0.5 font-mono text-caption text-fg">{t}</li>)}
              </ul>
            )}
          </div>
          <Meter label="Consultas SQL parametrizadas" value={arch.sql.parameterized} max={arch.sql.total} tone="bg-verified"
            detail={arch.sql.concatenated ? `${arch.sql.concatenated} se construyen concatenando texto: posible inyección SQL.` : "Ninguna consulta se construye por concatenación."} />
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
    <Section eyebrow="Módulos" title="Dependencias entre módulos" aside={arch.circular_dependencies.length ? <span className="text-danger">▲ {arch.circular_dependencies.length} ciclo{arch.circular_dependencies.length === 1 ? "" : "s"}</span> : "Sin ciclos"}>
      {arch.circular_dependencies.length > 0 && (
        <ul className="mb-4 space-y-1">
          {arch.circular_dependencies.map((cycle) => (
            <li key={cycle.join(">")} className="font-mono text-caption text-danger">↻ {cycle.join(" → ")} <span className="text-subtle">· romper el ciclo antes de extraer cualquiera de estos módulos</span></li>
          ))}
        </ul>
      )}
      <table className="w-full text-left">
        <thead><tr className="border-b border-line text-micro tracking-eyebrow text-subtle uppercase">
          <th className="py-2 font-medium">Módulo</th>
          <th className="py-2 text-right font-medium" title="Módulos que lo llaman">Fan-in</th>
          <th className="py-2 text-right font-medium" title="Módulos a los que llama">Fan-out</th>
          <th className="py-2 pl-6 font-medium">Depende de (llamadas)</th>
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
