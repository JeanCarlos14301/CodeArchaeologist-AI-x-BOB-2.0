import { useRef, useState } from "react";
import { Timeline } from "../components/Timeline";
import { Button, Card, ErrorState, ModeBadge } from "../components/ui";
import type { BobStatus, FlowJob } from "../types";

const MAX_ZIP_MB = 5; // backend/app/pipeline/ingestion.py: MAX_ZIP_COMPRESSED_BYTES

export interface StartRequest {
  file: File;
  token: string;
}

interface Props {
  offline: boolean;
  bob: BobStatus | null;
  bobError: string | null;
  busy: boolean;
  job: FlowJob | null;
  jobs: FlowJob[];
  error: string | null;
  onStart: (request: StartRequest) => void;
  onOpenImported: () => void;
  onSelectJob: (id: string) => void;
  onOpenResults: () => void;
}

export function HomeView({ offline, bob, bobError, busy, job, jobs, error, onStart, onOpenImported, onSelectJob, onOpenResults }: Props) {
  const [token, setToken] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const pickFile = (candidate: File | undefined) => {
    setFileError(null);
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".zip")) return setFileError("El archivo debe ser un .zip");
    if (candidate.size > MAX_ZIP_MB * 1024 * 1024) return setFileError(`El ZIP supera ${MAX_ZIP_MB} MB`);
    setFile(candidate);
  };

  const bobReady = bob ? bob.installed && bob.api_key_configured : true;
  const canLaunch = !busy && !offline && bobReady && file !== null && token.trim() !== "";

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-line bg-gradient-to-br from-accent/10 via-surface to-surface px-6 py-8 sm:px-10">
        <p className="font-mono text-xs uppercase tracking-widest text-accent">CodeArchaeologist × IBM Bob</p>
        <h1 className="mt-2 max-w-3xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          Entiende un sistema heredado en minutos, con evidencia en cada línea.
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Sube tu repositorio y IBM Bob lo audita de verdad. Cada hallazgo se comprueba contra el código y solo se muestra si su archivo, líneas y fragmento existen.
        </p>
        <ul className="mt-5 flex flex-wrap gap-2 text-xs">
          {["Análisis real con IBM Bob", "Evidencia verificada por código", "Sin datos de ejemplo"].map((item) => (
            <li key={item} className="rounded-full border border-line bg-surface px-3 py-1 text-muted">✓ {item}</li>
          ))}
        </ul>
      </section>

      {offline && <ErrorState message="No se pudo contactar con el backend. Arráncalo para poder auditar." />}
      {error && <ErrorState message={error} />}
      {bob && !bobReady && (
        <ErrorState message={!bob.installed ? "IBM Bob Shell no está instalado en el servidor: no se puede auditar." : "El servidor no tiene BOB_API_KEY configurada: no se puede auditar."} />
      )}

      <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div>
          <h2 className="text-sm font-semibold">Vitrina pública · FacturaYa</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted">Recorre una auditoría real grabada, marcada como importada. No requiere token ni consume bobcoins.</p>
        </div>
        <Button onClick={onOpenImported} disabled={busy || offline} className="shrink-0 px-5 py-2.5">Ver auditoría real de FacturaYa →</Button>
      </Card>

      <Card className="p-5 sm:p-6">
        <h2 className="mb-4 text-sm font-semibold">Auditar en vivo</h2>
        <div
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); pickFile(event.dataTransfer.files[0]); }}
          className={`rounded-xl border-2 border-dashed p-6 text-center transition ${dragging ? "border-accent bg-accent/5" : "border-line"}`}
        >
          <input ref={input} type="file" accept=".zip" className="sr-only" aria-label="Seleccionar ZIP" onChange={(event) => pickFile(event.target.files?.[0])} />
          <p className="text-sm">{file ? <><strong>{file.name}</strong> · {(file.size / 1024).toFixed(0)} KB</> : "Arrastra el .zip de tu repositorio aquí o"}</p>
          <Button variant="ghost" className="mt-2" onClick={() => input.current?.click()}>Elegir archivo</Button>
          {fileError && <p role="alert" className="mt-2 text-sm text-bad">{fileError}</p>}
          <p className="mt-2 text-xs text-muted">Python 3 + Flask + SQLite · máximo {MAX_ZIP_MB} MB. El contenido se analiza de forma estática y nunca se ejecuta.</p>
        </div>

        <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
          <label className="block text-sm">
            <span className="mb-1 block text-muted">Token de acceso (obligatorio)</span>
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              autoComplete="off"
              className="w-72 max-w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm"
            />
            <span className="mt-1 block text-xs text-muted">Cada auditoría gasta bobcoins del equipo, por eso siempre se pide.</span>
          </label>
          <Button onClick={() => file && onStart({ file, token: token.trim() })} disabled={!canLaunch} className="px-6 py-2.5">
            {busy ? "Auditoría en curso…" : "Auditar repositorio →"}
          </Button>
        </div>
      </Card>

      {job && (
        <Card className="p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold">Progreso</h2>
              <ModeBadge mode={job.execution_mode} />
              <span className="font-mono text-xs text-muted">{job.label}</span>
            </div>
            {job.status === "done" && <Button onClick={onOpenResults}>Ver resultados →</Button>}
          </div>
          <Timeline job={job} />
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold">Historial</h2>
          {jobs.length === 0 ? (
            <p className="text-sm text-muted">Aún no hay auditorías. Sube el primer ZIP arriba.</p>
          ) : (
            <ul className="space-y-1">
              {jobs.slice(0, 6).map((item) => (
                <li key={item.id}>
                  <button type="button" onClick={() => onSelectJob(item.id)} className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-2 ${job?.id === item.id ? "bg-surface-2" : ""}`}>
                    <span className="min-w-0 truncate"><span className="font-mono text-xs">{item.id}</span> <span className="text-muted">· {item.label}</span></span>
                    <span className="flex shrink-0 items-center gap-2"><ModeBadge mode={item.execution_mode} /><span className={`text-xs ${item.status === "failed" ? "text-bad" : item.status === "done" ? "text-ok" : "text-warn"}`}>{item.status}</span></span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold">IBM Bob</h2>
          {bobError ? (
            <p className="text-sm text-muted">No se pudo consultar el estado de Bob.</p>
          ) : !bob ? (
            <p className="text-sm text-muted">Consultando Bob…</p>
          ) : (
            <ul className="space-y-1.5 text-sm">
              <li className={bob.installed ? "text-ok" : "text-bad"}>{bob.installed ? `● Bob Shell ${bob.version ?? ""}` : "● Bob Shell no instalado"}</li>
              <li className={bob.api_key_configured ? "text-ok" : "text-bad"}>{bob.api_key_configured ? "● API key configurada" : "● Falta BOB_API_KEY"}</li>
              <li className="text-muted">{bob.custom_modes.length} modos · {bob.subagents.length} subagentes · {bob.skills.length} skills</li>
              <li className="text-xs text-muted">Límite por auditoría: {bob.max_cost_per_run} bobcoins · {Math.round(bob.timeout_s / 60)} min</li>
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
