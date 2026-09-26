import { useCallback } from "react";
import { api } from "../api";
import { Mermaid } from "../components/Mermaid";
import { Button, Card, EmptyState, ErrorState, Loading, PageHeader } from "../components/ui";
import type { Theme } from "../lib/theme";
import { useLoaded } from "../lib/useLoaded";

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-[11px] uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </Card>
  );
}

export function ArchitectureView({ jobId, token, theme, onGoHome }: { jobId: string | null; token: string; theme: Theme; onGoHome: () => void }) {
  const load = useCallback((id: string) => api.architecture(id, token), [token]);
  const { data, error, retry, loading } = useLoaded(load, jobId);

  if (!jobId) {
    return (
      <>
        <PageHeader title="Arquitectura" />
        <EmptyState title="Aún no hay arquitectura" action={<Button onClick={onGoHome}>Ir a Inicio</Button>}>
          Termina una auditoría para ver la arquitectura medida sobre tu código.
        </EmptyState>
      </>
    );
  }
  if (error) return <><PageHeader title="Arquitectura" /><ErrorState message={error} onRetry={retry} /></>;
  if (loading || !data) return <><PageHeader title="Arquitectura" /><Loading label="Analizando el código…" /></>;

  const noSql = data.sql.total === 0;

  return (
    <>
      <PageHeader title="Arquitectura actual" subtitle="Medida con análisis estático (AST, SQL y complejidad ciclomática) sobre el código que subiste. No hay estimaciones ni datos de ejemplo." />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Archivos Python" value={data.totals.files} />
        <Stat label="Funciones" value={data.totals.functions} />
        <Stat label="Llamadas entre funciones" value={data.totals.calls} />
        <Stat label="Consultas SQL" value={data.sql.total} hint={noSql ? "No se detectaron" : `${data.sql.concatenated} concatenadas · ${data.sql.parameterized} parametrizadas`} />
      </div>

      <Card className="mt-5 p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Módulos y dependencias</h2>
          <ul className="flex flex-wrap gap-3 text-xs text-muted" aria-label="Leyenda">
            {[["#38bdf8", "Sin hallazgos"], ["#fb7185", "Crítico"], ["#fb923c", "Alto"], ["#fbbf24", "Medio"], ["#94a3b8", "Bajo"]].map(([color, label]) => (
              <li key={label} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: color }} aria-hidden />{label}</li>
            ))}
          </ul>
        </div>
        <p className="mb-3 text-xs text-muted">Cada flecha indica cuántas llamadas hay de un archivo a otro. El color es la mayor severidad de los hallazgos validados en ese archivo.</p>
        {data.mermaid ? <Mermaid chart={data.mermaid} theme={theme} /> : <EmptyState title="Sin módulos">No se encontraron archivos Python para graficar.</EmptyState>}
      </Card>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card className="overflow-x-auto p-5">
          <h2 className="mb-3 text-sm font-semibold">Rutas HTTP ({data.routes.length})</h2>
          {data.routes.length === 0 ? (
            <p className="text-sm text-muted">No se detectaron rutas Flask.</p>
          ) : (
            <table className="w-full text-sm">
              <tbody className="divide-y divide-line">
                {data.routes.map((route) => (
                  <tr key={`${route.file}:${route.line_start}`}>
                    <td className="py-2 pr-3 font-mono text-xs"><span className="rounded bg-accent/10 px-1.5 py-0.5 text-accent">{route.methods.join(",")}</span> {route.rule}</td>
                    <td className="py-2 text-right font-mono text-xs text-muted">{route.file}:{route.line_start}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card className="overflow-x-auto p-5">
          <h2 className="mb-3 text-sm font-semibold">Funciones más complejas</h2>
          {data.complex_functions.length === 0 ? (
            <p className="text-sm text-muted">No se pudo medir la complejidad.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-muted">
                  <th className="pb-2 font-medium">Función</th>
                  <th className="pb-2 text-right font-medium">Complejidad</th>
                  <th className="pb-2 text-right font-medium">Líneas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.complex_functions.map((fn) => (
                  <tr key={`${fn.file}:${fn.line_start}`}>
                    <td className="py-2 pr-3"><span className="font-mono text-xs">{fn.name}</span> <span className="font-mono text-[11px] text-muted">{fn.file}:{fn.line_start}</span></td>
                    <td className="py-2 text-right font-mono text-xs">{fn.complexity} <span className="text-muted">({fn.rank})</span></td>
                    <td className="py-2 text-right font-mono text-xs">{fn.lines}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold">Dependencias circulares</h2>
          {data.circular_dependencies.length === 0 ? (
            <p className="text-sm text-muted">No se detectaron.</p>
          ) : (
            <ul className="space-y-1 font-mono text-xs">
              {data.circular_dependencies.map((cycle) => <li key={cycle.join(">")} className="text-warn">{cycle.join(" → ")}</li>)}
            </ul>
          )}
        </Card>
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold">Tablas detectadas</h2>
          {data.tables.length === 0 ? (
            <p className="text-sm text-muted">No se detectaron tablas en scripts SQL.</p>
          ) : (
            <ul className="flex flex-wrap gap-2">{data.tables.map((table) => <li key={table} className="rounded-lg border border-line bg-surface-2 px-3 py-1 font-mono text-xs">{table}</li>)}</ul>
          )}
        </Card>
      </div>
    </>
  );
}
