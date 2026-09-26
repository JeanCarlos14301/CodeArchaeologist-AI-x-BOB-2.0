import { api } from "../api";
import { Button, Card, EmptyState, PageHeader } from "../components/ui";

const FILES = [
  { name: "dossier.json" as const, format: "JSON", label: "Expediente validado", description: "Hallazgos con evidencia por archivo y línea, comprobados por código, más las métricas del validador." },
  { name: "bob-result.json" as const, format: "JSON", label: "Respuesta cruda de Bob", description: "Salida original de `bob run`, tal como la devolvió IBM Bob antes de validar." },
];

export function DownloadsView({ jobId, onGoHome }: { jobId: string | null; onGoHome: () => void }) {
  if (!jobId) {
    return (
      <>
        <PageHeader title="Descargas" />
        <EmptyState title="Aún no hay archivos" action={<Button onClick={onGoHome}>Ir a Inicio</Button>}>Termina una auditoría para descargar sus resultados.</EmptyState>
      </>
    );
  }
  return (
    <>
      <PageHeader title="Centro de descargas" subtitle="Archivos reales generados por esta auditoría." />
      <div className="grid gap-4 md:grid-cols-2">
        {FILES.map((file) => (
          <Card key={file.name} className="flex flex-col p-5">
            <span className="w-fit rounded-md bg-surface-2 px-2 py-0.5 font-mono text-xs text-accent">{file.format}</span>
            <h2 className="mt-3 font-semibold">{file.label}</h2>
            <p className="mt-1 flex-1 text-sm text-muted">{file.description}</p>
            <a href={api.downloadUrl(jobId, file.name)} download={file.name} className="mt-4 inline-flex items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:brightness-110">
              Descargar {file.name}
            </a>
          </Card>
        ))}
      </div>
    </>
  );
}
