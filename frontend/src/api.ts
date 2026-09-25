import {
  EXAMPLE_ARCHITECTURE,
  EXAMPLE_DOWNLOADS,
  EXAMPLE_MIGRATION,
} from "./fixtures";
import type {
  ArchitectureView,
  AuditDetail,
  BobStatus,
  DownloadsView,
  ExecutionMode,
  Job,
  MigrationView,
  SampleInfo,
  SourceExcerpt,
} from "./types";

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
  startAudit: (sample: string, executionMode: ExecutionMode) =>
    request<Job>("/api/audits", {
      method: "POST",
      body: JSON.stringify({ sample, execution_mode: executionMode }),
    }),
  source: (id: string, path: string, start: number, end: number) => {
    const query = new URLSearchParams({ path, start: String(start), end: String(end) });
    return request<SourceExcerpt>(`/api/audits/${encodeURIComponent(id)}/source?${query}`);
  },
};

export interface Loaded<T> {
  data: T;
  /** "api" si vino del backend; "fixture" si se usó el dato de ejemplo por falta de endpoint. */
  origin: "api" | "fixture";
}

/**
 * Pide un endpoint y cae al fixture si el backend no responde o aún no lo expone (404/0/501).
 * Cuando Daniel congele el contrato basta con publicar el endpoint: el fixture deja de usarse.
 */
async function withFallback<T>(path: string, fallback: T): Promise<Loaded<T>> {
  try {
    return { data: await request<T>(path), origin: "api" };
  } catch (error) {
    if (error instanceof ApiError && [0, 404, 405, 501].includes(error.status)) {
      return { data: fallback, origin: "fixture" };
    }
    throw error;
  }
}

export const views = {
  architecture: (id: string) => withFallback<ArchitectureView>(`/api/audits/${encodeURIComponent(id)}/architecture`, EXAMPLE_ARCHITECTURE),
  migration: (id: string) => withFallback<MigrationView>(`/api/audits/${encodeURIComponent(id)}/migration`, EXAMPLE_MIGRATION),
  downloads: (id: string) => withFallback<DownloadsView>(`/api/audits/${encodeURIComponent(id)}/downloads`, EXAMPLE_DOWNLOADS),
};
