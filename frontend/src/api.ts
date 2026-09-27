import type { ActivityPage, ArchitectureData, AssessRequest, StackReport, StudioState, AskAnswer, AskContext, AskStep, AuditDetail, BobStatus, GraphData, Job, MigrationViewData, SourceExcerpt } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

const NO_BACKEND = "Could not reach the server. Is the backend running?";

async function readError(response: Response): Promise<ApiError> {
  let detail = `Error ${response.status}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    // non-JSON body: the generic message stays
  }
  return new ApiError(detail, response.status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(NO_BACKEND, 0);
  }
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

const enc = encodeURIComponent;
/** The token header only when there is a token: in open mode the server needs none. */
const auth = (token?: string): Record<string, string> => (token ? { "X-Live-Token": token } : {});

export const api = {
  bobStatus: () => request<BobStatus>("/api/bob/status"),
  audits: (token?: string) => request<Job[]>("/api/audits", { headers: auth(token) }),
  audit: (id: string, token?: string) => request<AuditDetail>(`/api/audits/${enc(id)}`, { headers: auth(token) }),
  graph: (id: string, token?: string) => request<GraphData>(`/api/audits/${enc(id)}/graph`, { headers: auth(token) }),
  architecture: (id: string, token?: string) => request<ArchitectureData>(`/api/audits/${enc(id)}/architecture`, { headers: auth(token) }),
  migration: (id: string, token?: string) => request<MigrationViewData>(`/api/audits/${enc(id)}/migration`, { headers: auth(token) }),
  events: (id: string, after: number, token?: string) =>
    request<ActivityPage>(`/api/audits/${enc(id)}/events?after=${after}`, { headers: auth(token) }),
  source: (id: string, path: string, start: number, end: number, token?: string) => {
    const query = new URLSearchParams({ path, start: String(start), end: String(end) });
    return request<SourceExcerpt>(`/api/audits/${enc(id)}/source?${query}`, { headers: auth(token) });
  },
  /** Opens the showcase from a real recorded reply; it never invokes Bob or spends bobcoins. */
  imported: () => request<Job>("/api/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sample: "facturaya-v1", execution_mode: "imported" }),
  }),
  /** Uploads the ZIP and starts the real audit with Bob. The token is only needed in locked mode. */
  upload: (file: File, token: string, purpose: "audit" | "modernization" = "audit") => {
    const form = new FormData();
    form.set("zip_file", file);
    form.set("purpose", purpose);
    return request<Job>("/api/audits/upload", { method: "POST", body: form, headers: auth(token) });
  },
  stack: (id: string, token?: string) => request<StackReport>(`/api/audits/${enc(id)}/modernization/stack`, { headers: auth(token) }),
  studio: (id: string, token?: string) => request<StudioState>(`/api/audits/${enc(id)}/modernization`, { headers: auth(token) }),
  studioAssess: (id: string, body: AssessRequest, token: string) =>
    request<StudioState>(`/api/audits/${enc(id)}/modernization/assess`, {
      method: "POST", headers: { "Content-Type": "application/json", ...auth(token) }, body: JSON.stringify(body),
    }),
  studioPlan: (id: string, token: string) =>
    request<StudioState>(`/api/audits/${enc(id)}/modernization/plan`, { method: "POST", headers: auth(token) }),
  studioImplement: (id: string, token: string) =>
    request<StudioState>(`/api/audits/${enc(id)}/modernization/implement`, {
      method: "POST", headers: { "Content-Type": "application/json", ...auth(token) }, body: JSON.stringify({ confirm: true }),
    }),
  studioDownload: async (id: string, name: "modernized.zip" | "migration.diff", token?: string) => {
    const response = await fetch(`/api/audits/${enc(id)}/modernization/download/${name}`, { headers: auth(token) });
    if (!response.ok) throw await readError(response);
    return response.blob();
  },
  /** Contextual question to IBM Bob (ask mode, read-only). Spends bobcoins; the token is only needed in locked mode. */
  ask: (id: string, question: string, context: AskContext, token: string, requestId?: string) =>
    request<AskAnswer>(`/api/audits/${enc(id)}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth(token) },
      body: JSON.stringify({ question, context, request_id: requestId }),
    }),
  /** What Bob is doing to answer (reads, searches...). Polled while it answers. */
  askProgress: (id: string, requestId: string, after: number, token: string) =>
    request<{ steps: AskStep[] }>(`/api/audits/${enc(id)}/ask/${enc(requestId)}/progress?after=${after}`, { headers: auth(token) }),
  download: async (id: string, name: "dossier.json" | "bob-result.json" | "board_memo.docx" | "migration.diff", token?: string) => {
    const response = await fetch(`/api/audits/${enc(id)}/files/${name}`, { headers: auth(token) });
    if (!response.ok) throw await readError(response);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  },
};
