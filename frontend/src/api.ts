import {
  EXAMPLE_ARCHITECTURE,
  EXAMPLE_DOWNLOADS,
  EXAMPLE_JOB,
  EXAMPLE_MIGRATION,
} from "./fixtures";
import { adaptArchitecture, adaptDownloads, adaptMigration } from "./lib/jobsAdapter";
import type {
  ArchitectureView,
  AuditDetail,
  BobStatus,
  DossierResultRaw,
  DownloadsView,
  EngineId,
  ExecutionMode,
  GraphData,
  Job,
  JobStatusRaw,
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

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
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

let engine: EngineId = "audits";
export const setEngine = (value: EngineId) => {
  engine = value;
};
export const getEngine = (): EngineId => engine;

export type SourceType = "demo" | "holdout" | "zip";

const resultCache = new Map<string, Promise<DossierResultRaw>>();

export const jobsApi = {
  /** El motor /api/jobs puede estar apagado (ENABLE_JOBS_API=false en el despliegue público). */
  async available(): Promise<boolean> {
    try {
      await request<JobStatusRaw[]>("/api/jobs");
      return true;
    } catch (error) {
      if (error instanceof ApiError && [404, 405].includes(error.status)) return false;
      throw error;
    }
  },
  list: () => request<JobStatusRaw[]>("/api/jobs"),
  status: (id: string) => request<JobStatusRaw>(`/api/jobs/${encodeURIComponent(id)}`),
  result(id: string): Promise<DossierResultRaw> {
    const cached = resultCache.get(id);
    if (cached) return cached;
    const pending = request<DossierResultRaw>(`/api/jobs/${encodeURIComponent(id)}/result`);
    pending.then(undefined, () => resultCache.delete(id));
    resultCache.set(id, pending);
    return pending;
  },
  graph: (id: string) => request<GraphData>(`/api/jobs/${encodeURIComponent(id)}/graph`),
  async start(source: SourceType, mode: ExecutionMode, zip?: File): Promise<{ job_id: string }> {
    const form = new FormData();
    form.set("source_type", source);
    form.set("execution_mode", mode);
    if (zip) form.set("zip_file", zip);
    let response: Response;
    try {
      response = await fetch("/api/jobs", { method: "POST", body: form });
    } catch {
      throw new ApiError("No se pudo contactar con el servidor. ¿Está corriendo el backend?", 0);
    }
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
      throw new ApiError(typeof body.detail === "string" ? body.detail : `Error ${response.status}`, response.status);
    }
    return (await response.json()) as { job_id: string };
  },
};

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
    const base = engine === "jobs" ? "/api/jobs" : "/api/audits";
    return request<SourceExcerpt>(`${base}/${encodeURIComponent(id)}/source?${query}`);
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

/** Datos derivados del expediente real (motor /api/jobs) o, si no aplica, del endpoint del motor de auditorías. */
async function derived<T>(
  id: string,
  path: string,
  fixture: T,
  build: (result: DossierResultRaw) => T | Promise<T>,
): Promise<Loaded<T>> {
  if (id === EXAMPLE_JOB.id) return { data: fixture, origin: "fixture" };
  if (engine === "jobs") return { data: await build(await jobsApi.result(id)), origin: "api" };
  return withFallback<T>(`/api/audits/${encodeURIComponent(id)}/${path}`, fixture);
}

export const views = {
  architecture: (id: string) => derived<ArchitectureView>(id, "architecture", EXAMPLE_ARCHITECTURE, adaptArchitecture),
  migration: (id: string) => derived<MigrationView>(id, "migration", EXAMPLE_MIGRATION, (result) => adaptMigration(result, id, request)),
  downloads: (id: string) => derived<DownloadsView>(id, "downloads", EXAMPLE_DOWNLOADS, (result) => adaptDownloads(result, id)),
};
