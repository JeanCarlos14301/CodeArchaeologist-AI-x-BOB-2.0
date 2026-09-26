import { useCallback } from "react";
import { api } from "../api";
import { CodeBlock, toLines } from "../components/CodeBlock";
import { Button, Card, EmptyState, ErrorState, Loading, PageHeader } from "../components/ui";
import { useLoaded } from "../lib/useLoaded";

const STATUS = {
  passed: { label: "PASÓ", className: "bg-ok/10 text-ok ring-ok/30" },
  failed: { label: "FALLÓ", className: "bg-bad/10 text-bad ring-bad/30" },
  not_run: { label: "NO EJECUTADA", className: "bg-warn/10 text-warn ring-warn/30" },
} as const;

export function MigrationView({ jobId, token, onGoHome }: { jobId: string | null; token: string; onGoHome: () => void }) {
  const load = useCallback((id: string) => api.migration(id, token), [token]);
  const { data, error, retry, loading } = useLoaded(load, jobId);

  if (!jobId) return <><PageHeader title="Migración" /><EmptyState title="Aún no hay un primer corte" action={<Button onClick={onGoHome}>Ir a Inicio</Button>}>Termina una auditoría para consultar la implementación y sus pruebas.</EmptyState></>;
  if (error) return <><PageHeader title="Migración" /><ErrorState message={error} onRetry={retry} /></>;
  if (loading || !data) return <><PageHeader title="Migración" /><Loading label="Cargando primer corte…" /></>;

  const state = STATUS[data.result.status];
  return (
    <>
      <PageHeader
        title="Primer corte de migración"
        subtitle={data.result.implementation_origin}
        right={<span className={`rounded-md px-2 py-1 text-xs font-semibold ring-1 ring-inset ${state.className}`}>{state.label}</span>}
      />
      {data.result.status === "not_run" ? (
        <EmptyState title="Pruebas no ejecutadas">{data.result.reason ?? "No hay una ejecución disponible para esta auditoría."}</EmptyState>
      ) : (
        <div className="space-y-5">
          <Card className="overflow-x-auto p-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Pruebas reales de caracterización</h2>
              <span className="font-mono text-xs text-muted">{data.result.endpoint}</span>
            </div>
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-xs text-muted"><th className="pb-2">Destino</th><th className="pb-2">Prueba</th><th className="pb-2">Resultado</th><th className="pb-2 text-right">Duración</th></tr></thead>
              <tbody className="divide-y divide-line">
                {data.result.tests.map((test, index) => {
                  const status = STATUS[test.status];
                  return <tr key={`${test.target}-${test.name}-${index}`}><td className="py-2 font-mono text-xs">{test.target}</td><td className="py-2">{test.name}{test.reason && <span className="block text-xs text-bad">{test.reason}</span>}</td><td className="py-2"><span className={`rounded px-1.5 py-0.5 text-xs ring-1 ring-inset ${status.className}`}>{status.label}</span></td><td className="py-2 text-right font-mono text-xs">{Math.round(test.duration_ms)} ms</td></tr>;
                })}
              </tbody>
            </table>
          </Card>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card className="min-w-0 p-4"><h2 className="mb-3 text-sm font-semibold">Legado</h2>{data.legacy_code ? <CodeBlock path={data.result.legacy_file ?? "app.py"} lines={toLines(data.legacy_code, 1)} /> : <p className="text-sm text-muted">No disponible.</p>}</Card>
            <Card className="min-w-0 p-4"><h2 className="mb-1 text-sm font-semibold">Moderno</h2><p className="mb-3 text-xs text-muted">Implementación de referencia del equipo; no generada por Bob.</p>{data.modern_code ? <CodeBlock path={data.result.modern_file ?? "modern/invoices_api.py"} lines={toLines(data.modern_code, 1)} /> : <p className="text-sm text-muted">No disponible.</p>}</Card>
          </div>
        </div>
      )}
    </>
  );
}
