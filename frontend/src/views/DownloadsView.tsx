import { api } from "../api";
import { Button, Card, EmptyState, PageHeader } from "../components/ui";

const FILES = [
  { name: "dossier.json" as const, format: "JSON", label: "Expediente validado", description: "Hallazgos con evidencia por archivo y línea, comprobados por código, más las métricas del validador." },
  { name: "bob-result.json" as const, format: "JSON", label: "Respuesta cruda de Bob", description: "Salida original de `bob run`, tal como la devolvió IBM Bob antes de validar." },
  { name: "board_memo.docx" as const, format: "DOCX", label: "Memorando para la junta", description: "Riesgo, radio de impacto y rango PERT calculados desde el expediente y el grafo de esta auditoría." },
  { name: "migration.diff" as const, format: "DIFF", label: "Primer corte de referencia", description: "Parche unificado de la implementación Strangler Fig probada para la muestra registrada." },
];

export function DownloadsView({ jobId, token, hasMigrationDiff, onGoHome }: { jobId: string | null; token: string; hasMigrationDiff: boolean; onGoHome: () => void }) {
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
        {FILES.filter((file) => file.name !== "migration.diff" || hasMigrationDiff).map((file) => (
          <Card key={file.name} className="flex flex-col p-5">
            <span className="w-fit rounded-md bg-surface-2 px-2 py-0.5 font-mono text-xs text-accent">{file.format}</span>
            <h2 className="mt-3 font-semibold">{file.label}</h2>
            <p className="mt-1 flex-1 text-sm text-muted">{file.description}</p>
            <button type="button" onClick={() => void api.download(jobId, file.name, token)} className="mt-4 inline-flex items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:brightness-110">
              Descargar {file.name}
            </button>
          </Card>
        ))}
      </div>
    </>
  );
}
