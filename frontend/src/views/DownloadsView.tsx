import { views } from "../api";
import { Card, EmptyState, ErrorState, FixtureNotice, Loading, ModeBadge, PageHeader } from "../components/ui";
import { useLoaded } from "../lib/useLoaded";

export function DownloadsView({ jobId }: { jobId: string | null }) {
  const { result, error, retry, loading } = useLoaded(views.downloads, jobId);

  if (!jobId) return <><PageHeader title="Descargas" /><EmptyState title="Aún no hay archivos">Lanza una auditoría para generar el memo, el expediente y el corte de migración.</EmptyState></>;
  if (error) return <><PageHeader title="Descargas" /><ErrorState message={error} onRetry={retry} /></>;
  if (loading || !result) return <><PageHeader title="Descargas" /><Loading /></>;

  const { data, origin } = result;
  return (
    <>
      <PageHeader title="Centro de descargas" subtitle="Entregables generados a partir del expediente." right={<ModeBadge mode={data.execution_mode} />} />
      <FixtureNotice show={origin === "fixture"} />
      {data.items.length === 0 ? (
        <EmptyState title="No hay archivos disponibles">Esta auditoría todavía no generó entregables.</EmptyState>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {data.items.map((item) => (
            <Card key={item.id} className="flex flex-col p-5">
              <span className="w-fit rounded-md bg-surface-2 px-2 py-0.5 font-mono text-xs text-accent">{item.format}</span>
              <h2 className="mt-3 font-semibold">{item.label}</h2>
              <p className="mt-1 flex-1 text-sm text-muted">{item.description}</p>
              {item.url ? (
                <a href={item.url} download={item.filename} className="mt-4 inline-flex items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:brightness-110">
                  Descargar {item.filename}
                </a>
              ) : (
                <span className="mt-4 rounded-lg border border-dashed border-line px-4 py-2 text-center text-xs text-muted">Disponible cuando el backend genere el archivo</span>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
