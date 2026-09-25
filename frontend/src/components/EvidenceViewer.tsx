import { useEffect, useState } from "react";
import { api } from "../api";
import type { Evidence, SourceExcerpt } from "../types";

const CONTEXT_LINES = 6;

interface Props {
  jobId: string;
  evidence: Evidence | null;
}

export function EvidenceViewer({ jobId, evidence }: Props) {
  const [excerpt, setExcerpt] = useState<SourceExcerpt | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!evidence) return;
    let cancelled = false;
    setError(null);
    api
      .source(jobId, evidence.path, Math.max(1, evidence.line_start - CONTEXT_LINES), evidence.line_end + CONTEXT_LINES)
      .then((data) => !cancelled && setExcerpt(data))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [jobId, evidence]);

  if (!evidence) {
    return <p className="text-sm text-stone-500">Selecciona una evidencia para ver el código citado.</p>;
  }
  if (error) return <p className="text-sm text-rose-700">{error}</p>;
  if (!excerpt) return <p className="text-sm text-stone-500">Cargando código…</p>;

  return (
    <div className="overflow-hidden rounded-md border border-stone-800 bg-stone-950">
      <p className="border-b border-stone-800 px-3 py-1.5 font-mono text-xs text-stone-300">
        {excerpt.path} · líneas {evidence.line_start}–{evidence.line_end} de {excerpt.total_lines}
      </p>
      <pre className="max-h-[60vh] overflow-auto py-2 text-[12px] leading-5">
        {excerpt.lines.map((line) => {
          const cited = line.number >= evidence.line_start && line.number <= evidence.line_end;
          return (
            <div key={line.number} className={`flex px-3 ${cited ? "bg-amber-400/20" : ""}`}>
              <span className="mr-3 w-8 shrink-0 select-none text-right text-stone-500">{line.number}</span>
              <code className={`whitespace-pre ${cited ? "text-amber-100" : "text-stone-300"}`}>{line.text || " "}</code>
            </div>
          );
        })}
      </pre>
    </div>
  );
}
