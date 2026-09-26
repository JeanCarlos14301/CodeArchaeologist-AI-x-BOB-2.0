import { useState } from "react";
import { Download } from "lucide-react";
import { api } from "../api";
import { Button } from "../components/ui/Button";
import { ScreenHeader, Section } from "../components/ui/Layout";
import { useWorkspace } from "../lib/workspace";
import type { Dossier } from "../types";
import { JobGate } from "./JobGate";

type FileName = "dossier.json" | "bob-result.json" | "board_memo.docx" | "migration.diff";

const FILES: { name: FileName; format: string; label: string; audience: string; description: string }[] = [
  { name: "board_memo.docx", format: "DOCX", label: "Memorando para la junta", audience: "Dirección", description: "Riesgo, radio de impacto y rango PERT en lenguaje de negocio, calculados desde el expediente y el grafo." },
  { name: "dossier.json", format: "JSON", label: "Expediente técnico validado", audience: "Ingeniería", description: "Hallazgos con evidencia por archivo y línea comprobada por código, métricas del validador, riesgo y PERT." },
  { name: "migration.diff", format: "DIFF", label: "Parche del primer corte", audience: "Revisión de código", description: "Diff unificado de la implementación Strangler Fig probada, listo para revisión humana." },
  { name: "bob-result.json", format: "JSON", label: "Respuesta cruda de IBM Bob", audience: "Auditoría", description: "Salida original de `bob run` antes de validar: permite reproducir y auditar el análisis." },
];

export function ReportsView() {
  return <JobGate>{(dossier) => <Reports dossier={dossier} />}</JobGate>;
}

function Reports({ dossier }: { dossier: Dossier }) {
  const { route, token } = useWorkspace();
  const [busy, setBusy] = useState<FileName | null>(null);
  const [errors, setErrors] = useState<Partial<Record<FileName, string>>>({});
  const available = FILES.filter((file) => file.name !== "migration.diff" || !!dossier.migration?.diff_file);

  const download = async (name: FileName) => {
    if (!route.jobId) return;
    setBusy(name);
    setErrors((current) => ({ ...current, [name]: undefined }));
    try {
      await api.download(route.jobId, name, token);
    } catch (err) {
      setErrors((current) => ({ ...current, [name]: (err as Error).message }));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="px-6 py-6 @3xl:px-10">
      <ScreenHeader eyebrow="Reportes · Entregables del análisis" title={`${available.length} archivos generados`} description="Todo lo que se descarga sale de este análisis concreto; ninguna cifra se añade al generar el documento." />
      <Section>
        <ul className="divide-y divide-line border-y border-line">
          {available.map((file) => (
            <li key={file.name} className="grid items-center gap-x-6 gap-y-2 py-4 @2xl:grid-cols-[4rem_minmax(0,1fr)_auto]">
              <span className="w-fit rounded-tick border border-line-strong px-1.5 py-0.5 font-mono text-micro text-fg-2">{file.format}</span>
              <div className="min-w-0">
                <p className="text-body text-fg">{file.label} <span className="text-caption text-subtle">· {file.audience}</span></p>
                <p className="mt-0.5 text-caption text-pretty text-muted">{file.description}</p>
                {errors[file.name] && <p role="alert" className="mt-1 text-caption text-danger">✗ {errors[file.name]}</p>}
              </div>
              <Button size="sm" disabled={busy !== null} onClick={() => void download(file.name)} icon={<Download size={14} aria-hidden />}>
                {busy === file.name ? "Descargando…" : `Descargar ${file.name}`}
              </Button>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
