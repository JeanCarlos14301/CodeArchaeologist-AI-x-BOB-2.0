import type { AuditDetail, BobStatus, ExecutionMode, Job, SampleInfo, SourceExcerpt } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  } catch {
    throw new ApiError("No se pudo contactar con el servidor. ¿Está corriendo el backend?", 0);
  }
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // cuerpo no JSON: se mantiene el mensaje genérico
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  bobStatus: () => request<BobStatus>("/api/bob/status"),
  samples: () => request<SampleInfo[]>("/api/samples"),
  audits: () => request<Job[]>("/api/audits"),
  audit: (id: string) => request<AuditDetail>(`/api/audits/${encodeURIComponent(id)}`),
  startAudit: (sample: string, executionMode: ExecutionMode, liveToken = "") =>
    request<Job>("/api/audits", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(executionMode === "live" && liveToken ? { "X-Live-Token": liveToken } : {}),
      },
      body: JSON.stringify({ sample, execution_mode: executionMode }),
    }),
  source: (id: string, path: string, start: number, end: number) => {
    const query = new URLSearchParams({ path, start: String(start), end: String(end) });
    return request<SourceExcerpt>(`/api/audits/${encodeURIComponent(id)}/source?${query}`);
  },
};
