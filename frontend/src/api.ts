import type { ActivityPage, ArchitectureData, AskAnswer, AskContext, AuditDetail, BobStatus, GraphData, Job, MigrationViewData, SourceExcerpt } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

const NO_BACKEND = "No se pudo contactar con el servidor. ¿Está corriendo el backend?";

async function readError(response: Response): Promise<ApiError> {
  let detail = `Error ${response.status}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    // cuerpo no JSON: se mantiene el mensaje genérico
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
const auth = (token?: string): HeadersInit | undefined => token ? { "X-Live-Token": token } : undefined;

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
  /** Abre la vitrina a partir de una respuesta real grabada; no invoca Bob ni consume bobcoins. */
  imported: () => request<Job>("/api/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sample: "facturaya-v1", execution_mode: "imported" }),
  }),
  /** Sube el ZIP y lanza la auditoría real con Bob. El token es obligatorio. */
  upload: (file: File, token: string) => {
    const form = new FormData();
    form.set("zip_file", file);
    return request<Job>("/api/audits/upload", { method: "POST", body: form, headers: { "X-Live-Token": token } });
  },
  /** Pregunta contextual a IBM Bob (modo ask, solo lectura). Siempre exige token: gasta bobcoins. */
  ask: (id: string, question: string, context: AskContext, token: string) =>
    request<AskAnswer>(`/api/audits/${enc(id)}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Live-Token": token },
      body: JSON.stringify({ question, context }),
    }),
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
