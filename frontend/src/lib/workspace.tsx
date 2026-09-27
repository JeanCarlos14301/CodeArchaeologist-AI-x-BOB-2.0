import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ApiError, api } from "../api";
import type { ArchitectureData, AskAnswer, AskContext, AskStep, BobStatus, Dossier, FlowJob, GraphData, MigrationViewData, PipelineEvent, SourceExcerpt } from "../types";
import { isActive, jobToFlow } from "./flow";
import { useHashRoute, type Route, type Section } from "./router";
import { parseRequirements, type DeclaredPackage } from "./stack";

const POLL_INTERVAL_MS = 1500;
const PANEL_KEY = "ca-ai-panel";

/** Resources derived from a finished analysis; requested once per job and cached. */
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
  /** What Bob is doing while it answers (live). */
  progress: AskStep[];
  /** Moment (epoch s) the question was sent. */
  startedAt: number;
}

const ASK_PROGRESS_MS = 900;

/** Random question identifier used to follow its progress (in the format the backend accepts). */
function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID().replace(/-/g, "");
  return Array.from({ length: 24 }, () => Math.floor(Math.random() * 36).toString(36)).join("");
}

interface WorkspaceValue {
  route: Route;
  navigate: (next: Partial<Route>) => void;
  go: (section: Section, extra?: Partial<Route>) => void;
  token: string;
  setToken: (token: string) => void;
  /** The server is in locked mode (LIVE_AUDIT_TOKEN set): Bob calls and uploads need the token. */
  tokenRequired: boolean;
  /** Bob can be called right now: open mode, or locked mode with a token entered. */
  hasAccess: boolean;
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
  /** Activity of each stage of the current analysis (polled while it runs). */
  activity: PipelineEvent[];
  activityReady: boolean;
  ask: (question: string, context: AskContext) => Promise<void>;
  composerSeed: { text: string; nonce: number } | null;
  seedComposer: (text: string) => void;
  clearComposerSeed: () => void;
}

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return value;
}

/** Subscribes a view to a resource of the current analysis and requests it if it is not loaded yet. */
export function useResource<K extends ResourceKind>(kind: K): ResourceState<Resources[K]> & { retry: () => void } {
  const { resource, requestResource, flow } = useWorkspace();
  // Projects uploaded only for modernization have no audit: there is no architecture or graph to request.
  const done = flow?.status === "done" && flow.purpose !== "modernization";
  useEffect(() => {
    if (done) requestResource(kind);
  }, [done, kind, requestResource]);
  return { ...resource(kind), retry: () => requestResource(kind) };
}

function readPanelPreference(): boolean {
  // On small screens the panel is a modal drawer: it starts closed so it does not cover the work.
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

  // The question history belongs to the analysis: it resets when the job changes, not when the token changes.
  useEffect(() => setAskHistory([]), [jobId]);

  // Activity by stage: cursor by `seq`; polled while the analysis runs, completed when it finishes.
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

  // Loads and polls the analysis selected in the URL until it finishes.
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

  // The token is part of the key: a response requested without a token (403) never blocks the one with a token.
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
      // The showcase opens Bob's recorded session, playing.
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
      // no persistence: the preference lasts for the session
    }
  }, []);

  const graph = resource("graph").data;
  const aiContext = useMemo(() => deriveContext(route, dossier, graph), [route, dossier, graph]);

  const ask = useCallback(async (question: string, context: AskContext) => {
    if (!jobId) return;
    const id = ++askId.current;
    const requestId = newRequestId();
    setAskHistory((history) => [...history, { id, question, context, status: "pending", progress: [], startedAt: Date.now() / 1000 }]);
    const update = (change: (entry: AskEntry) => AskEntry) =>
      setAskHistory((history) => history.map((entry) => (entry.id === id ? change(entry) : entry)));

    // While Bob answers, what it really does is shown (reads, searches, skills).
    let answered = false;
    let after = 0;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const page = await api.askProgress(jobId, requestId, after, token);
        if (!answered && page.steps.length > 0) {
          after = page.steps[page.steps.length - 1].seq;
          update((entry) => ({ ...entry, progress: [...entry.progress, ...page.steps] }));
        }
      } catch {
        // Progress is optional: the answer arrives anyway through the main request.
      }
      if (!answered) timer = window.setTimeout(poll, ASK_PROGRESS_MS);
    };
    timer = window.setTimeout(poll, ASK_PROGRESS_MS);
    try {
      const answer = await api.ask(jobId, question, context, token, requestId);
      answered = true;
      update((entry) => ({ ...entry, status: "done", answer, progress: answer.activity?.length ? answer.activity : entry.progress }));
    } catch (err) {
      answered = true;
      update((entry) => ({ ...entry, status: "error", error: (err as Error).message }));
    } finally {
      window.clearTimeout(timer);
    }
  }, [jobId, token]);

  const clearComposerSeed = useCallback(() => setComposerSeed(null), []);
  const seedComposer = useCallback((text: string) => {
    setAiOpen(true);
    setComposerSeed({ text, nonce: Date.now() });
  }, [setAiOpen]);

  const tokenRequired = bob?.live_requires_token ?? false;
  const value: WorkspaceValue = {
    route, navigate, go, token, setToken, tokenRequired, hasAccess: !tokenRequired || token.trim().length > 0,
    bob, offline, jobs, flow, dossier, accessDenied, jobError,
    notice, dismissNotice: () => setNotice(null), startUpload, openShowcase, resource, requestResource,
    aiOpen, setAiOpen, paletteOpen, setPaletteOpen, aiContext, askHistory, ask, composerSeed, seedComposer, clearComposerSeed,
    activity, activityReady,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

/** The context the AI sees is the object the person is inspecting in the URL. */
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
