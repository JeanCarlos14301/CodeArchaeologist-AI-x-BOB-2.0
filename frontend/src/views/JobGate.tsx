import { useState, type FormEvent, type ReactNode } from "react";
import type { Dossier } from "../types";
import { useWorkspace } from "../lib/workspace";
import { AnalysisConsole } from "../components/domain/console/AnalysisConsole";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorState, Loading } from "../components/ui/States";

/** Estados comunes de un análisis antes de mostrar una vista: privado, error, en curso, fallido. */
export function JobGate({ children }: { children: (dossier: Dossier) => ReactNode }) {
  const { flow, dossier, accessDenied, jobError, offline, setToken, navigate } = useWorkspace();

  if (offline && !flow) {
    return <Frame><ErrorState title="No hay conexión con el backend." message="GET /api/audits no respondió." hint="Arranca el servidor (uvicorn app.main:app) y recarga la página." /></Frame>;
  }
  if (accessDenied) return <Frame><TokenPrompt onSubmit={setToken} /></Frame>;
  if (jobError) {
    return (
      <Frame>
        <ErrorState title="No se pudo abrir este análisis." message={jobError} hint="Puede que el identificador no exista en este servidor." onRetry={() => navigate({ jobId: null })} retryLabel="Volver a Proyectos" />
      </Frame>
    );
  }
  if (!flow) return <Frame><Loading label="Cargando análisis…" /></Frame>;
  if (flow.status !== "done" || !dossier) {
    // Mientras corre (o si falló), cualquier sección muestra la sesión en vivo con su actividad real.
    return (
      <Frame>
        <AnalysisConsole autoplay={false} />
        {flow.status === "failed" && (
          <div className="mt-6"><Button variant="secondary" onClick={() => navigate({ jobId: null })}>Volver a Proyectos para reintentar</Button></div>
        )}
      </Frame>
    );
  }
  return <>{children(dossier)}</>;
}

function Frame({ children }: { children: ReactNode }) {
  return <div className="px-6 py-6 @3xl:px-10">{children}</div>;
}

function TokenPrompt({ onSubmit }: { onSubmit: (token: string) => void }) {
  const [value, setValue] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (value.trim()) onSubmit(value.trim());
  };
  return (
    <EmptyState title="Este análisis es privado">
      <p>Proviene de un repositorio subido y su código solo se muestra con el token de acceso con el que se creó.</p>
      <form onSubmit={submit} className="mt-4 flex flex-wrap gap-2">
        <label htmlFor="gate-token" className="sr-only">Token de acceso</label>
        <input id="gate-token" type="password" autoComplete="off" value={value} onChange={(event) => setValue(event.target.value)}
          placeholder="X-Live-Token" className="h-9 w-72 max-w-full rounded-pill border border-line bg-control px-4 font-mono text-caption text-fg placeholder:text-subtle focus:border-focus focus:outline-none" />
        <Button type="submit" variant="secondary" disabled={!value.trim()}>Desbloquear análisis</Button>
      </form>
    </EmptyState>
  );
}
