import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ApiError, api } from "../api";
import type { ArchitectureData, AskAnswer, AskContext, BobStatus, Dossier, FlowJob, GraphData, MigrationViewData, PipelineEvent, SourceExcerpt } from "../types";
import { isActive, jobToFlow } from "./flow";
import { useHashRoute, type Route, type Section } from "./router";
import { parseRequirements, type DeclaredPackage } from "./stack";

const POLL_INTERVAL_MS = 1500;
const PANEL_KEY = "ca-ai-panel";

/** Recursos derivados de un análisis terminado; se piden una vez por job y se cachean. */
interface Resources {
  architecture: ArchitectureData;
  graph: GraphData;
  migration: MigrationViewData;
  requirements: DeclaredPackage[];
}
export type ResourceKind = keyof Resources;

interface ResourceState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

export interface AskEntry {
  id: number;
  question: string;
  context: AskContext;
  status: "pending" | "done" | "error";
  answer?: AskAnswer;
  error?: string;
}

interface WorkspaceValue {
  route: Route;
  navigate: (next: Partial<Route>) => void;
  go: (section: Section, extra?: Partial<Route>) => void;
  token: string;
  setToken: (token: string) => void;
  bob: BobStatus | null;
  offline: boolean;
  jobs: FlowJob[];
  flow: FlowJob | null;
  dossier: Dossier | null;
  accessDenied: boolean;
  jobError: string | null;
  notice: string | null;
  dismissNotice: () => void;
  startUpload: (file: File, token: string, purpose?: "audit" | "modernization") => Promise<void>;
  openShowcase: () => Promise<void>;
  resource: <K extends ResourceKind>(kind: K) => ResourceState<Resources[K]>;
  requestResource: (kind: ResourceKind) => void;
  aiOpen: boolean;
  setAiOpen: (open: boolean) => void;
  paletteOpen: boolean;
  setPaletteOpen: (open: boolean) => void;
  aiContext: AskContext;
  askHistory: AskEntry[];
  /** Actividad de cada etapa del análisis actual (se sondea mientras corre). */
  activity: PipelineEvent[];
  activityReady: boolean;
  ask: (question: string, context: AskContext) => Promise<void>;
  composerSeed: { text: string; nonce: number } | null;
  seedComposer: (text: string) => void;
}

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace debe usarse dentro de <WorkspaceProvider>");
  return value;
}

/** Suscribe una vista a un recurso del análisis actual y lo pide si aún no está cargado. */
export function useResource<K extends ResourceKind>(kind: K): ResourceState<Resources[K]> & { retry: () => void } {
  const { resource, requestResource, flow } = useWorkspace();
  // Los proyectos subidos solo para modernizar no tienen auditoría: no hay arquitectura ni grafo que pedir.
  const done = flow?.status === "done" && flow.purpose !== "modernization";
  useEffect(() => {
    if (done) requestResource(kind);
  }, [done, kind, requestResource]);
  return { ...resource(kind), retry: () => requestResource(kind) };
}

function readPanelPreference(): boolean {
  // En pantallas pequeñas el panel es un cajón modal: empieza cerrado para no tapar el trabajo.
  if (!window.matchMedia("(min-width: 1024px)").matches) return false;
  try {
    return localStorage.getItem(PANEL_KEY) !== "closed";
  } catch {
    return true;
  }
}

function loaderFor(kind: ResourceKind, jobId: string, token: string): Promise<unknown> {
  switch (kind) {
    case "architecture":
      return api.architecture(jobId, token);
    case "graph":
      return api.graph(jobId, token);
    case "migration":
      return api.migration(jobId, token);
    case "requirements":
      return api
        .source(jobId, "requirements.txt", 1, 400, token)
        .then((excerpt: SourceExcerpt) => parseRequirements(excerpt.lines))
        .catch((err: Error) => {
          if (err instanceof ApiError && err.status === 404) return [];
          throw err;
        });
  }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [route, navigate] = useHashRoute();
  const [token, setToken] = useState("");
  const [bob, setBob] = useState<BobStatus | null>(null);
  const [offline, setOffline] = useState(false);
  const [jobs, setJobs] = useState<FlowJob[]>([]);
  const [flow, setFlow] = useState<FlowJob | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [resources, setResources] = useState<Record<string, ResourceState<unknown>>>({});
  const [aiOpen, setAiOpenState] = useState(readPanelPreference);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [askHistory, setAskHistory] = useState<AskEntry[]>([]);
  const [composerSeed, setComposerSeed] = useState<{ text: string; nonce: number } | null>(null);
  const askId = useRef(0);
  const jobId = route.jobId;

  const fail = useCallback((err: Error) => {
    if (err instanceof ApiError && err.status === 0) setOffline(true);
    else setNotice(err.message);
  }, []);

  const refreshJobs = useCallback(() => {
    api.audits(token).then((list) => {
      setOffline(false);
      setJobs(list.map(jobToFlow));
    }).catch(fail);
  }, [token, fail]);

  useEffect(() => {
    api.bobStatus().then(setBob).catch(fail);
  }, [fail]);

  useEffect(() => {
    refreshJobs();
  }, [refreshJobs]);

  // El historial de preguntas pertenece al análisis: se reinicia al cambiar de job, no al cambiar el token.
  useEffect(() => setAskHistory([]), [jobId]);

  // Actividad por etapas: cursor por `seq`; mientras el análisis corre se sondea, al terminar se completa.
  const [activity, setActivity] = useState<PipelineEvent[]>([]);
  const [activityReady, setActivityReady] = useState(false);
  const running = !!flow && isActive(flow);
  const finished = flow?.status === "done" || flow?.status === "failed";
  useEffect(() => {
    setActivity([]);
    setActivityReady(false);
  }, [jobId]);
  const cursor = useRef({ job: "", after: 0 });
  useEffect(() => {
    if (!jobId || (!running && !finished)) return;
    if (cursor.current.job !== jobId) cursor.current = { job: jobId, after: 0 };
    let cancelled = false;
    let timer: number | undefined;
    const pull = async () => {
      try {
        let page = await api.events(jobId, cursor.current.after, token);
        const fresh = [...page.events];
        while (page.has_more && !cancelled) {
          page = await api.events(jobId, page.next_after, token);
          fresh.push(...page.events);
        }
        if (cancelled) return;
        cursor.current.after = page.next_after;
        if (fresh.length) setActivity((current) => [...current, ...fresh]);
        if (running) timer = window.setTimeout(pull, POLL_INTERVAL_MS);
        else setActivityReady(true);
      } catch {
        if (!cancelled && running) timer = window.setTimeout(pull, POLL_INTERVAL_MS);
        else if (!cancelled) setActivityReady(true);
      }
    };
    void pull();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [jobId, token, running, finished]);

  // Carga y sondea el análisis seleccionado en la URL hasta que termine.
  useEffect(() => {
    setFlow(null);
    setDossier(null);
    setAccessDenied(false);
    setJobError(null);
    if (!jobId) return;
    let cancelled = false;
    let timer: number | undefined;
    const load = () => {
      api
        .audit(jobId, token)
        .then((data) => {
          if (cancelled) return;
          setOffline(false);
          setAccessDenied(false);
          setFlow(jobToFlow(data.job));
          setDossier(data.dossier);
          if (isActive(data.job)) timer = window.setTimeout(load, POLL_INTERVAL_MS);
          else refreshJobs();
        })
        .catch((err: Error) => {
          if (cancelled) return;
          if (err instanceof ApiError && err.status === 403) setAccessDenied(true);
          else if (err instanceof ApiError && err.status === 0) setOffline(true);
          else setJobError(err.message);
        });
    };
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [jobId, token, refreshJobs]);

  // El token forma parte de la clave: una respuesta pedida sin token (403) nunca bloquea la pedida con token.
  const resource = useCallback(<K extends ResourceKind>(kind: K): ResourceState<Resources[K]> => {
    const key = `${jobId}:${token}:${kind}`;
    return (resources[key] as ResourceState<Resources[K]> | undefined) ?? { data: null, error: null, loading: false };
  }, [jobId, token, resources]);

  const inflight = useRef(new Set<string>());
  const loaded = useRef(new Set<string>());
  const requestResource = useCallback((kind: ResourceKind) => {
    if (!jobId) return;
    const key = `${jobId}:${token}:${kind}`;
    if (inflight.current.has(key) || loaded.current.has(key)) return;
    inflight.current.add(key);
    setResources((state) => ({ ...state, [key]: { data: null, error: null, loading: true } }));
    loaderFor(kind, jobId, token)
      .then((data) => {
        loaded.current.add(key);
        setResources((state) => ({ ...state, [key]: { data, error: null, loading: false } }));
      })
      .catch((err: Error) => setResources((state) => ({ ...state, [key]: { data: null, error: err.message, loading: false } })))
      .finally(() => inflight.current.delete(key));
  }, [jobId, token]);

  const go = useCallback((section: Section, extra: Partial<Route> = {}) => {
    if (jobId) navigate({ jobId, section, ...extra });
  }, [jobId, navigate]);

  const openJob = useCallback((id: string, section: Section = "overview", play = false) => navigate({ jobId: id, section, play }), [navigate]);

  const startUpload = useCallback(async (file: File, uploadToken: string, purpose: "audit" | "modernization" = "audit") => {
    setNotice(null);
    setToken(uploadToken);
    try {
      const job = await api.upload(file, uploadToken, purpose);
      refreshJobs();
      openJob(job.id, purpose === "modernization" ? "modernization" : "session");
    } catch (err) {
      fail(err as Error);
    }
  }, [fail, openJob, refreshJobs]);

  const openShowcase = useCallback(async () => {
    setNotice(null);
    try {
      const job = await api.imported();
      refreshJobs();
      // La vitrina abre la sesión grabada de Bob reproduciéndose.
      openJob(job.id, "session", true);
    } catch (err) {
      fail(err as Error);
    }
  }, [fail, openJob, refreshJobs]);

  const setAiOpen = useCallback((open: boolean) => {
    setAiOpenState(open);
    try {
      localStorage.setItem(PANEL_KEY, open ? "open" : "closed");
    } catch {
      // sin persistencia: la preferencia dura la sesión
    }
  }, []);

  const graph = resource("graph").data;
  const aiContext = useMemo(() => deriveContext(route, dossier, graph), [route, dossier, graph]);

  const ask = useCallback(async (question: string, context: AskContext) => {
    if (!jobId) return;
    const id = ++askId.current;
    setAskHistory((history) => [...history, { id, question, context, status: "pending" }]);
    const settle = (patch: Partial<AskEntry>) =>
      setAskHistory((history) => history.map((entry) => (entry.id === id ? { ...entry, ...patch } : entry)));
    try {
      const answer = await api.ask(jobId, question, context, token);
      settle({ status: "done", answer });
    } catch (err) {
      settle({ status: "error", error: (err as Error).message });
    }
  }, [jobId, token]);

  const seedComposer = useCallback((text: string) => {
    setAiOpen(true);
    setComposerSeed({ text, nonce: Date.now() });
  }, [setAiOpen]);

  const value: WorkspaceValue = {
    route, navigate, go, token, setToken, bob, offline, jobs, flow, dossier, accessDenied, jobError,
    notice, dismissNotice: () => setNotice(null), startUpload, openShowcase, resource, requestResource,
    aiOpen, setAiOpen, paletteOpen, setPaletteOpen, aiContext, askHistory, ask, composerSeed, seedComposer,
    activity, activityReady,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

/** El contexto que ve la IA es el objeto que la persona inspecciona en la URL. */
function deriveContext(route: Route, dossier: Dossier | null, graph: GraphData | null): AskContext {
  if (route.finding && dossier) {
    const finding = [...dossier.findings, ...dossier.rejected_findings].find((item) => item.id === route.finding);
    if (finding) {
      const evidence = finding.evidence[0];
      return { kind: "finding", finding_id: finding.id, label: finding.title, path: evidence?.path, line_start: evidence?.line_start, line_end: evidence?.line_end };
    }
  }
  if (route.node && graph) {
    const node = graph.nodes.find((item) => item.id === route.node);
    if (node) return { kind: "function", label: node.qualname, path: node.file, line_start: node.line_start, line_end: node.line_end };
  }
  if (route.file) {
    return route.section === "architecture" || route.section === "dependencies"
      ? { kind: "module", label: route.file, path: route.file }
      : { kind: "file", label: route.file, path: route.file, line_start: route.line ?? undefined };
  }
  return { kind: "project", label: dossier?.repo_name };
}
