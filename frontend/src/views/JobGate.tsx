import { useState, type FormEvent, type ReactNode } from "react";
import type { Dossier } from "../types";
import { useWorkspace } from "../lib/workspace";
import { AnalysisConsole } from "../components/domain/console/AnalysisConsole";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorState, Loading } from "../components/ui/States";

/** Common states of an analysis before a view is shown: private, error, running, failed. */
export function JobGate({ children }: { children: (dossier: Dossier) => ReactNode }) {
  const { flow, dossier, accessDenied, jobError, offline, setToken, navigate, go } = useWorkspace();

  if (offline && !flow) {
    return <Frame><ErrorState title="No connection to the backend." message="GET /api/audits did not answer." hint="Start the server (uvicorn app.main:app) and reload the page." /></Frame>;
  }
  if (accessDenied) return <Frame><TokenPrompt onSubmit={setToken} /></Frame>;
  if (jobError) {
    return (
      <Frame>
        <ErrorState title="This analysis could not be opened." message={jobError} hint="The identifier may not exist on this server." onRetry={() => navigate({ jobId: null })} retryLabel="Back to Projects" />
      </Frame>
    );
  }
  if (!flow) return <Frame><Loading label="Loading the analysis…" /></Frame>;
  if (flow.status === "done" && !dossier) {
    return (
      <Frame>
        <EmptyState
          title="This project was uploaded for modernization only."
          action={<Button variant="secondary" onClick={() => go("modernization")}>Go to the Modernization Studio</Button>}
        >
          It was not audited with evidence, so there are no findings, risks or dossier. The stack, the assessment and the migration plan are in Modernization.
        </EmptyState>
      </Frame>
    );
  }
  if (flow.status !== "done" || !dossier) {
    // While it runs (or if it failed), any section shows the live session with its real activity.
    return (
      <Frame>
        <AnalysisConsole autoplay={false} />
        {flow.status === "failed" && (
          <div className="mt-6"><Button variant="secondary" onClick={() => navigate({ jobId: null })}>Back to Projects to retry</Button></div>
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
    <EmptyState title="This analysis is private">
      <p>It comes from an uploaded repository and its code is only shown with the access token it was created with.</p>
      <form onSubmit={submit} className="mt-4 flex flex-wrap gap-2">
        <label htmlFor="gate-token" className="sr-only">Access token</label>
        <input id="gate-token" type="password" autoComplete="off" value={value} onChange={(event) => setValue(event.target.value)}
          placeholder="X-Live-Token" className="h-9 w-72 max-w-full rounded-pill border border-line bg-control px-4 font-mono text-caption text-fg placeholder:text-subtle focus:border-focus focus:outline-none" />
        <Button type="submit" variant="secondary" disabled={!value.trim()}>Unlock the analysis</Button>
      </form>
    </EmptyState>
  );
}

/** Like JobGate but without requiring a dossier: the Modernization Studio works with any uploaded project. */
export function StudioGate({ children }: { children: () => ReactNode }) {
  const { flow, accessDenied, jobError, offline, setToken, navigate } = useWorkspace();
  if (offline && !flow) return <Frame><ErrorState title="No connection to the backend." message="GET /api/audits did not answer." hint="Start the server (uvicorn app.main:app) and reload the page." /></Frame>;
  if (accessDenied) return <Frame><TokenPrompt onSubmit={setToken} /></Frame>;
  if (jobError) return <Frame><ErrorState title="This analysis could not be opened." message={jobError} onRetry={() => navigate({ jobId: null })} retryLabel="Back to Projects" /></Frame>;
  if (!flow) return <Frame><Loading label="Loading the project…" /></Frame>;
  if (flow.status !== "done") {
    return (
      <Frame>
        <AnalysisConsole autoplay={false} />
        {flow.status === "failed" && <div className="mt-6"><Button variant="secondary" onClick={() => navigate({ jobId: null })}>Back to Projects to retry</Button></div>}
      </Frame>
    );
  }
  return <>{children()}</>;
}
