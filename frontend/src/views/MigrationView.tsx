import { views } from "../api";
import { CodeBlock, toLines } from "../components/CodeBlock";
import { Card, EmptyState, ErrorState, FixtureNotice, Loading, ModeBadge, PageHeader } from "../components/ui";
import { useLoaded } from "../lib/useLoaded";
import type { TestStatus } from "../types";

const TEST_INFO: Record<TestStatus, { label: string; icon: string; tone: string }> = {
  passed: { label: "Pasó", icon: "✓", tone: "text-ok bg-ok/10 ring-ok/30" },
  failed: { label: "Falló", icon: "✗", tone: "text-bad bg-bad/10 ring-bad/30" },
  not_run: { label: "No ejecutada", icon: "○", tone: "text-muted bg-surface-2 ring-line" },
};

export function MigrationView({ jobId }: { jobId: string | null }) {
  const { result, error, retry, loading } = useLoaded(views.migration, jobId);

  if (!jobId) return <><PageHeader title="Migración" /><EmptyState title="Aún no hay migración">Lanza una auditoría para ver el primer corte Strangler Fig.</EmptyState></>;
  if (error) return <><PageHeader title="Migración" /><ErrorState message={error} onRetry={retry} /></>;
  if (loading || !result) return <><PageHeader title="Migración" /><Loading /></>;

  const { data, origin } = result;
  const totals = (Object.keys(TEST_INFO) as TestStatus[]).map((status) => ({ status, count: data.tests.filter((t) => t.status === status).length }));

  return (
    <>
      <PageHeader title={`Migración · ${data.slice_name}`} subtitle={data.description} right={<ModeBadge mode={data.execution_mode} />} />
      <FixtureNotice show={origin === "fixture"} />

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold"><span className="rounded bg-bad/10 px-2 py-0.5 text-xs text-bad">Legado</span> Flask</p>
          <CodeBlock path={data.legacy.path} lines={toLines(data.legacy.code)} maxHeight="50vh" />
        </div>
        <div>
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold"><span className="rounded bg-ok/10 px-2 py-0.5 text-xs text-ok">Nuevo</span> FastAPI</p>
          <CodeBlock path={data.modern.path} lines={toLines(data.modern.code)} maxHeight="50vh" />
        </div>
      </div>

      <Card className="mt-6 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Pruebas de caracterización</h2>
          <ul className="flex gap-2 text-xs">
            {totals.map(({ status, count }) => (
              <li key={status} className={`rounded-md px-2 py-1 ring-1 ring-inset ${TEST_INFO[status].tone}`}>{TEST_INFO[status].icon} {TEST_INFO[status].label} · {count}</li>
            ))}
          </ul>
        </div>
        {data.tests.length === 0 ? (
          <p className="text-sm text-muted">Este corte aún no tiene pruebas.</p>
        ) : (
          <ul className="divide-y divide-line">
            {data.tests.map((test) => (
              <li key={test.id} className="flex items-start gap-3 py-3">
                <span className={`mt-0.5 shrink-0 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TEST_INFO[test.status].tone}`}>{TEST_INFO[test.status].icon} {TEST_INFO[test.status].label}</span>
                <div className="min-w-0">
                  <p className="text-sm font-medium">{test.name} <span className="font-mono text-xs text-muted">{test.id}</span></p>
                  <p className="text-xs text-muted">{test.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
