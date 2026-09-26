import { useRef, useState, type DragEvent } from "react";
import { ArrowRight, UploadCloud } from "lucide-react";
import { AnalysisStatus } from "../components/domain/AnalysisStatus";
import { ModeBadge, StatusDot } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataList, Eyebrow, Section, Segmented } from "../components/ui/Layout";
import { ErrorState } from "../components/ui/States";
import { formatDate, jobLabel } from "../lib/format";
import { isActive } from "../lib/flow";
import { useWorkspace } from "../lib/workspace";

const MAX_ZIP_MB = 5; // backend/app/pipeline/ingestion.py: MAX_ZIP_COMPRESSED_BYTES
type Source = "zip" | "github" | "local";

export function ProjectsView() {
  const { jobs, bob, offline, notice, dismissNotice, startUpload, openShowcase, navigate } = useWorkspace();
  const [source, setSource] = useState<Source>("zip");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [token, setTokenDraft] = useState("");
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const picker = useRef<HTMLInputElement>(null);

  const active = jobs.find((job) => isActive(job)) ?? null;
  const bobReady = bob ? bob.installed && bob.api_key_configured : false;
  const canStart = !offline && bobReady && !active && !!file && token.trim().length > 0 && !submitting;
  const blockedBy = offline ? "El backend no responde." : !bob ? "Consultando IBM Bob…" : !bobReady ? "IBM Bob no está listo en el servidor." : active ? "Ya hay un análisis en curso." : null;

  const pick = (candidate: File | undefined) => {
    setFileError(null);
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".zip")) return setFileError("El archivo debe ser un .zip del repositorio.");
    if (candidate.size > MAX_ZIP_MB * 1024 * 1024) return setFileError(`El ZIP pesa ${(candidate.size / 1024 / 1024).toFixed(1)} MB; el máximo es ${MAX_ZIP_MB} MB.`);
    setFile(candidate);
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files[0]);
  };

  const start = async () => {
    if (!file || !canStart) return;
    setSubmitting(true);
    await startUpload(file, token.trim());
    setSubmitting(false);
  };

  return (
    <div className="px-6 pt-10 pb-12 @3xl:px-10">
      <header className="max-w-3xl">
        <Eyebrow>CodeArchaeologist × IBM Bob</Eyebrow>
        <h1 className="mt-3 font-display text-display font-normal text-balance text-fg">
          Entiende un sistema heredado{" "}
          <span className="relative inline-block">
            antes de tocarlo.
            <span aria-hidden className="absolute -bottom-1 left-0 h-0.5 w-full rounded-pill bg-spectrum" />
          </span>
        </h1>
        <p className="mt-4 max-w-2xl text-body text-pretty text-muted">
          Conecta un repositorio. IBM Bob lo audita y cada hallazgo se comprueba contra el código —archivo, líneas y fragmento—
          antes de llegar a tu arquitectura, tus riesgos y tu plan de migración.
        </p>
      </header>

      {notice && (
        <div className="mt-6 max-w-3xl">
          <ErrorState title="La acción no se completó." message={notice} onRetry={dismissNotice} retryLabel="Descartar" />
        </div>
      )}

      <div className="mt-10 grid gap-x-12 gap-y-4 @5xl:grid-cols-[minmax(0,1fr)_minmax(300px,380px)]">
        <div>
          <Section eyebrow="01 · Conectar" title="Repositorio a analizar" className="pt-0">
            <Segmented<Source>
              label="Origen del repositorio"
              value={source}
              onChange={setSource}
              options={[
                { value: "zip", label: "Subir ZIP" },
                { value: "github", label: "GitHub", hint: "Requiere integración OAuth; aún no disponible" },
                { value: "local", label: "Carpeta local", hint: "Requiere un agente local; aún no disponible" },
              ]}
            />

            {source === "zip" ? (
              <div className="mt-5 space-y-4">
                <div
                  onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  className={`flex flex-col items-center rounded-composer border border-dashed px-6 py-9 text-center transition-[border-color,background-color] duration-150 ${dragging ? "border-accent-hover bg-raised" : "border-line-strong bg-surface"}`}
                >
                  <input ref={picker} type="file" accept=".zip,application/zip" className="sr-only" aria-label="Seleccionar el ZIP del repositorio" onChange={(event) => pick(event.target.files?.[0])} />
                  <UploadCloud size={22} aria-hidden className="text-subtle" />
                  {file ? (
                    <p className="mt-3 font-mono text-body text-fg">{file.name} <span className="text-subtle">· {(file.size / 1024).toFixed(0)} KB</span></p>
                  ) : (
                    <p className="mt-3 text-body text-fg-2">Arrastra aquí el .zip del repositorio</p>
                  )}
                  <Button size="sm" variant="ghost" className="mt-2" onClick={() => picker.current?.click()}>
                    {file ? "Elegir otro archivo" : "Elegir archivo"}
                  </Button>
                  {fileError && <p role="alert" className="mt-2 text-caption text-danger">{fileError}</p>}
                </div>

                <div className="grid gap-3 @xl:grid-cols-[minmax(0,1fr)_auto] @xl:items-end">
                  <label className="block min-w-0">
                    <span className="mb-1.5 block text-caption text-muted">Token de acceso (obligatorio: cada análisis consume bobcoins)</span>
                    <input type="password" autoComplete="off" value={token} onChange={(event) => setTokenDraft(event.target.value)}
                      className="h-9 w-full rounded-pill border border-line bg-control px-4 font-mono text-caption text-fg focus:border-focus focus:outline-none" />
                  </label>
                  <Button variant="primary" disabled={!canStart} onClick={() => void start()} icon={<ArrowRight size={14} aria-hidden />}>
                    {submitting ? "Enviando repositorio…" : "Iniciar análisis del repositorio"}
                  </Button>
                </div>
                <p className="text-caption text-subtle">
                  Python 3 + Flask + SQLite · hasta {MAX_ZIP_MB} MB · el código se analiza de forma estática y nunca se ejecuta.
                  {blockedBy && <span className="text-warning"> {blockedBy}</span>}
                </p>
              </div>
            ) : (
              <div className="mt-5 rounded-panel border border-dashed border-line-strong px-5 py-6">
                <p className="text-body text-fg">{source === "github" ? "Conexión con GitHub" : "Proyecto local"} · aún no disponible</p>
                <p className="mt-1 text-body text-pretty text-muted">
                  {source === "github"
                    ? "Necesita autorización OAuth y permisos de lectura por repositorio. Mientras tanto, descarga el repositorio como ZIP desde GitHub y súbelo."
                    : "Un navegador no puede leer tu disco de forma segura. Comprime la carpeta del proyecto en un ZIP y súbela."}
                </p>
                <Button size="sm" variant="secondary" className="mt-4" onClick={() => setSource("zip")}>Subir un ZIP en su lugar</Button>
              </div>
            )}
          </Section>

          {active && (
            <Section eyebrow="En curso" title={jobLabel(active.label)} aside={<ModeBadge mode={active.execution_mode} />}>
              <div className="max-w-xl"><AnalysisStatus flow={active} /></div>
              <Button size="sm" variant="secondary" className="mt-4" onClick={() => navigate({ jobId: active.id, section: "session" })}>Ver la sesión en vivo</Button>
            </Section>
          )}

          <Section eyebrow="Sin gastar bobcoins" title="Auditoría real de FacturaYa">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="max-w-lg text-body text-pretty text-muted">
                Recorre un análisis completo de un sistema de facturación Flask + SQLite: respuesta real de IBM Bob grabada, evidencia verificada y primer corte de migración probado.
              </p>
              <Button variant="secondary" disabled={offline} onClick={() => void openShowcase()}>Abrir auditoría de FacturaYa</Button>
            </div>
          </Section>
        </div>

        <aside className="space-y-0">
          <Section eyebrow="Historial" title="Análisis recientes" className="pt-0">
            {jobs.length === 0 ? (
              <p className="text-body text-muted">Todavía no hay análisis en este servidor.</p>
            ) : (
              <ul className="divide-y divide-line-subtle">
                {jobs.slice(0, 8).map((job) => (
                  <li key={job.id}>
                    <button type="button" onClick={() => navigate({ jobId: job.id, section: "overview" })} className="grid w-full grid-cols-[1fr_auto] items-center gap-x-3 gap-y-0.5 py-2.5 text-left hover:bg-raised">
                      <span className="truncate font-mono text-caption text-fg">{jobLabel(job.label)}</span>
                      <ModeBadge mode={job.execution_mode} />
                      <span className="text-caption text-subtle">{formatDate(job.created_at)}</span>
                      <span className="text-caption text-subtle">
                        <StatusDot tone={job.status === "done" ? "ok" : job.status === "failed" ? "bad" : "busy"} label={job.status === "done" ? "completo" : job.status === "failed" ? "falló" : "en curso"} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section eyebrow="Servidor" title="IBM Bob">
            {!bob ? (
              <p className="text-body text-muted">{offline ? "Sin conexión con el backend." : "Consultando…"}</p>
            ) : (
              <DataList rows={[
                { label: "Bob Shell", value: bob.installed ? <StatusDot tone="ok" label={bob.version ?? "instalado"} /> : <StatusDot tone="bad" label="no instalado" /> },
                { label: "API key", value: bob.api_key_configured ? <StatusDot tone="ok" label="configurada" /> : <StatusDot tone="bad" label="falta" /> },
                { label: "Modos · subagentes · skills", value: `${bob.custom_modes.length} · ${bob.subagents.length} · ${bob.skills.length}` },
                { label: "Límite por análisis", value: `${bob.max_cost_per_run} bc · ${Math.round(bob.timeout_s / 60)} min` },
              ]} />
            )}
          </Section>
        </aside>
      </div>
    </div>
  );
}
