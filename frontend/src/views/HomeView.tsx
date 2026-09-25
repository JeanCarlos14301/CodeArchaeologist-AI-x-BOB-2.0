import { useRef, useState } from "react";
import { Timeline } from "../components/Timeline";
import { Button, Card, ErrorState, ModeBadge } from "../components/ui";
import type { BobStatus, ExecutionMode, Job, SampleInfo } from "../types";

type Source = "demo" | "holdout" | "zip";

const MODES: { value: ExecutionMode; label: string; hint: string }[] = [
  { value: "example", label: "Ejemplo", hint: "Instantáneo, datos de ejemplo" },
  { value: "imported", label: "Importado", hint: "Respuesta real de Bob ya guardada" },
  { value: "live", label: "Live", hint: "Bob en vivo, ≈1–2 min y consume bobcoins" },
];

const MAX_ZIP_MB = 50;

interface Props {
  samples: SampleInfo[];
  offline: boolean;
  bob: BobStatus | null;
  bobError: string | null;
  busy: boolean;
  job: Job | null;
  jobs: Job[];
  error: string | null;
  onStartSample: (sample: string, mode: ExecutionMode, liveToken: string) => void;
  onStartFixture: (label: string) => void;
  onSelectJob: (id: string) => void;
  onOpenResults: () => void;
}

export function HomeView(props: Props) {
  const { samples, offline, bob, bobError, busy, job, jobs, error, onStartSample, onStartFixture, onSelectJob, onOpenResults } = props;
  const [source, setSource] = useState<Source>("demo");
  const [mode, setMode] = useState<ExecutionMode>("imported");
  const [liveToken, setLiveToken] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const demoSample = samples.find((item) => !/holdout/i.test(item.id)) ?? samples[0];
  const holdoutSample = samples.find((item) => /holdout/i.test(item.id));

  const pickFile = (candidate: File | undefined) => {
    setFileError(null);
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".zip")) return setFileError("El archivo debe ser un .zip");
    if (candidate.size > MAX_ZIP_MB * 1024 * 1024) return setFileError(`El ZIP supera ${MAX_ZIP_MB} MB`);
    setFile(candidate);
  };

  const launch = () => {
    if (source === "demo") {
      if (offline || !demoSample) onStartFixture("facturaya-v1");
      else onStartSample(demoSample.id, mode, liveToken);
    } else if (source === "holdout") {
      if (holdoutSample && !offline) onStartSample(holdoutSample.id, mode, liveToken);
      else onStartFixture("holdout");
    } else if (file) {
      onStartFixture(file.name);
    }
  };

  const useMode = source === "demo" && !offline;
  // On the public deployment the backend sets LIVE_AUDIT_TOKEN, so live runs (which spend the
  // team's bobcoins) need the X-Live-Token header. Locally the flag is false and nothing changes.
  const needsToken = useMode && mode === "live" && (bob?.live_requires_token ?? false);
  const canLaunch = !busy && (source !== "zip" || file !== null) && (!needsToken || liveToken !== "");

  const cards: { id: Source; icon: string; title: string; text: string; tag?: string }[] = [
    { id: "demo", icon: "▶", title: "Repositorio demo", text: "FacturaYa v1: Flask + SQLite con fallos reales para ver el flujo completo." },
    { id: "holdout", icon: "◐", title: "Repositorio holdout", text: "Segundo repositorio no visto, opcional, para comprobar que no está memorizado.", tag: holdoutSample ? undefined : "Sin backend aún" },
    { id: "zip", icon: "⇪", title: "Subir un ZIP", text: "Sube tu propio repositorio Python 3 + Flask + SQLite.", tag: "Sin backend aún" },
  ];

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-line bg-gradient-to-br from-accent/10 via-surface to-surface px-6 py-8 sm:px-10">
        <p className="font-mono text-xs uppercase tracking-widest text-accent">CodeArchaeologist × IBM Bob</p>
        <h1 className="mt-2 max-w-3xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          Entiende un sistema heredado en minutos, con evidencia en cada línea.
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Recibe un repositorio, devuelve hallazgos verificados por código, un memo para la junta con riesgos y esfuerzo, y un primer corte de migración probado.
        </p>
        <ul className="mt-5 flex flex-wrap gap-2 text-xs">
          {["Cada hallazgo apunta a archivo y línea", "Cifras calculadas por código, no por IA", "Migración Strangler Fig con pruebas"].map((item) => (
            <li key={item} className="rounded-full border border-line bg-surface px-3 py-1 text-muted">✓ {item}</li>
          ))}
        </ul>
      </section>

      {offline && (
        <p role="status" className="rounded-lg border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn">
          Backend no disponible: la app funciona en <strong>modo demostración</strong> con datos de ejemplo.
        </p>
      )}
      {error && <ErrorState message={error} />}

      <div>
        <h2 className="mb-3 text-sm font-semibold text-muted">1 · Elige qué analizar</h2>
        <div role="radiogroup" aria-label="Origen del repositorio" className="grid gap-3 md:grid-cols-3">
          {cards.map((card) => (
            <button
              key={card.id}
              type="button"
              role="radio"
              aria-checked={source === card.id}
              onClick={() => setSource(card.id)}
              className={`rounded-xl border p-4 text-left transition ${source === card.id ? "border-accent bg-accent/5 ring-1 ring-accent/40" : "border-line bg-surface hover:border-accent/40"}`}
            >
              <div className="flex items-center justify-between">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-2 text-accent" aria-hidden>{card.icon}</span>
                {card.tag && <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">{card.tag}</span>}
              </div>
              <h3 className="mt-3 font-semibold">{card.title}</h3>
              <p className="mt-1 text-sm text-muted">{card.text}</p>
            </button>
          ))}
        </div>

        {source === "zip" && (
          <div
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); pickFile(event.dataTransfer.files[0]); }}
            className={`mt-3 rounded-xl border-2 border-dashed p-6 text-center transition ${dragging ? "border-accent bg-accent/5" : "border-line"}`}
          >
            <input ref={input} type="file" accept=".zip" className="sr-only" aria-label="Seleccionar ZIP" onChange={(event) => pickFile(event.target.files?.[0])} />
            <p className="text-sm">{file ? <><strong>{file.name}</strong> · {(file.size / 1024).toFixed(0)} KB</> : "Arrastra tu .zip aquí o"}</p>
            <Button variant="ghost" className="mt-2" onClick={() => input.current?.click()}>Elegir archivo</Button>
            {fileError && <p role="alert" className="mt-2 text-sm text-bad">{fileError}</p>}
            <p className="mt-2 text-xs text-muted">El backend aún no acepta cargas: por ahora se recorre el flujo con datos de ejemplo. El contenido subido nunca se ejecuta.</p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4">
        {useMode ? (
          <fieldset>
            <legend className="mb-2 text-sm font-semibold text-muted">2 · Modo de ejecución</legend>
            <div className="flex flex-wrap gap-2">
              {MODES.map((option) => (
                <label key={option.value} title={option.hint} className={`cursor-pointer rounded-lg border px-3 py-2 text-sm transition ${mode === option.value ? "border-accent bg-accent/10 text-fg" : "border-line text-muted hover:border-accent/40"}`}>
                  <input type="radio" name="mode" className="sr-only" checked={mode === option.value} onChange={() => setMode(option.value)} />
                  <span className="font-medium">{option.label}</span>
                  <span className="ml-2 hidden text-xs text-muted md:inline">{option.hint}</span>
                </label>
              ))}
            </div>
            {needsToken && (
              <label className="mt-3 block text-sm">
                <span className="mb-1 block text-muted">Token de acceso a live</span>
                <input
                  type="password"
                  value={liveToken}
                  onChange={(event) => setLiveToken(event.target.value)}
                  autoComplete="off"
                  className="w-full max-w-xs rounded-lg border border-line bg-surface px-3 py-2 text-sm"
                />
                <span className="mt-1 block text-xs text-muted">
                  En la demo pública, live gasta bobcoins del equipo y pide token. Ejemplo e Importado no lo piden.
                </span>
              </label>
            )}
          </fieldset>
        ) : <span />}
        <Button onClick={launch} disabled={!canLaunch} className="px-6 py-2.5">
          {busy ? "Auditoría en curso…" : "Auditar repositorio →"}
        </Button>
      </div>

      {job && (
        <Card className="p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">Progreso</h2>
              <ModeBadge mode={job.execution_mode} />
              <span className="font-mono text-xs text-muted">{job.id}</span>
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
            <p className="text-sm text-muted">Aún no hay auditorías. Lanza la primera arriba.</p>
          ) : (
            <ul className="space-y-1">
              {jobs.slice(0, 6).map((item) => (
                <li key={item.id}>
                  <button type="button" onClick={() => onSelectJob(item.id)} className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-2 ${job?.id === item.id ? "bg-surface-2" : ""}`}>
                    <span className="min-w-0 truncate"><span className="font-mono text-xs">{item.id}</span> <span className="text-muted">· {item.sample}</span></span>
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
              <li className="text-xs text-muted">Límite live: {bob.max_cost_per_run} bobcoins · {Math.round(bob.timeout_s / 60)} min</li>
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
