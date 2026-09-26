import type { ArchitectureData, AuditDetail, BobStatus, GraphData, Job, SourceExcerpt } from "./types";

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

export const api = {
  bobStatus: () => request<BobStatus>("/api/bob/status"),
  audits: () => request<Job[]>("/api/audits"),
  audit: (id: string) => request<AuditDetail>(`/api/audits/${enc(id)}`),
  graph: (id: string) => request<GraphData>(`/api/audits/${enc(id)}/graph`),
  architecture: (id: string) => request<ArchitectureData>(`/api/audits/${enc(id)}/architecture`),
  source: (id: string, path: string, start: number, end: number) => {
    const query = new URLSearchParams({ path, start: String(start), end: String(end) });
    return request<SourceExcerpt>(`/api/audits/${enc(id)}/source?${query}`);
  },
  /** Sube el ZIP y lanza la auditoría real con Bob. El token es obligatorio. */
  upload: (file: File, token: string) => {
    const form = new FormData();
    form.set("zip_file", file);
    return request<Job>("/api/audits/upload", { method: "POST", body: form, headers: { "X-Live-Token": token } });
  },
  downloadUrl: (id: string, name: "dossier.json" | "bob-result.json") => `/api/audits/${enc(id)}/files/${name}`,
};
