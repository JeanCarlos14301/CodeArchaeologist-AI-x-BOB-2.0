import type {
  ArchitectureView,
  Dossier,
  DossierResultRaw,
  DownloadsView,
  EvidenceCheck,
  FlowJob,
  FlowStage,
  Finding,
  GraphData,
  Job,
  JobStatusRaw,
  MigrationTest,
  MigrationView,
  Severity,
  SourceExcerpt,
  TestReportRaw,
  TestStatus,
} from "../types";

/** Nombres de las 11 etapas del pipeline (backend/app/worker.py). Sirven para mostrar las pendientes. */
export const PIPELINE_STAGES = [
  "Ingesta Segura & Extractores",
  "Auditoría de Evidencia (Bob)",
  "Validador de Evidencia Física",
  "Arquitecto de Migración (Bob)",
  "Radio de Explosión & PERT",
  "Guardián de Contrato (Bob)",
  "Sandbox Pytest vs Legado",
  "Cirujano Strangler (Bob)",
  "Sandbox Pytest vs Nuevo",
  "Narrador Ejecutivo (Bob)",
  "Renderizadores de Artefactos",
] as const;

const SEVERITY: Record<DossierResultRaw["findings"][number]["severity"], Severity> = {
  CRITICAL: "critical",
  HIGH: "high",
  MEDIUM: "medium",
  LOW: "low",
  INFO: "info",
};

const TEST_STATUS: Record<"PASS" | "FAIL" | "SKIPPED", TestStatus> = { PASS: "passed", FAIL: "failed", SKIPPED: "not_run" };

// ---------------------------------------------------------------- flujo / estados

export function jobStatusToFlow(raw: JobStatusRaw): FlowJob {
  const finished = raw.status === "completed" || raw.status === "completed_with_warnings";
  const failed = raw.status === "failed" || raw.status === "cancelled";

  const stages: FlowStage[] = PIPELINE_STAGES.map((label, index) => {
    const number = index + 1;
    const events = raw.events.filter((event) => event.stage === number);
    const completed = events.find((event) => event.status === "completed");
    const started = events.find((event) => event.status === "started");
    let state: FlowStage["state"] = "pending";
    if (completed || finished) state = "done";
    else if (started) state = failed ? "failed" : "running";
    return {
      id: `stage-${number}`,
      number,
      label,
      state,
      duration_ms: completed?.duration_ms ?? null,
      message: (completed ?? started)?.message ?? null,
    };
  });

  const running = stages.find((stage) => stage.state === "running" || stage.state === "failed");
  return {
    id: raw.job_id,
    engine: "jobs",
    label: raw.source_type,
    execution_mode: raw.execution_mode as FlowJob["execution_mode"],
    status: finished ? "done" : failed ? "failed" : raw.status === "queued" ? "queued" : "running",
    progress: raw.progress_percent,
    current_stage: finished ? PIPELINE_STAGES.length : (running?.number ?? Math.max(raw.stage, 0)),
    stages,
    error: raw.error_message,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  };
}

const AUDIT_STAGES = [
  { id: "preparing", label: "Sandbox" },
  { id: "auditing", label: "Auditoría con Bob" },
  { id: "validating", label: "Validación" },
  { id: "done", label: "Expediente" },
] as const;

export function auditJobToFlow(job: Job): FlowJob {
  const done = job.status === "done";
  const failed = job.status === "failed";
  const index = AUDIT_STAGES.findIndex((stage) => stage.id === job.stage);
  const current = done ? AUDIT_STAGES.length : Math.max(index, 0);
  return {
    id: job.id,
    engine: "audits",
    label: job.sample,
    execution_mode: job.execution_mode,
    status: job.status,
    progress: Math.round((current / AUDIT_STAGES.length) * 100),
    current_stage: current + (done ? 0 : 1),
    stages: AUDIT_STAGES.map((stage, i) => ({
      id: stage.id,
      number: i + 1,
      label: stage.label,
      state: i < current ? "done" : i === current ? (failed ? "failed" : "running") : "pending",
      duration_ms: null,
      message: null,
    })),
    error: job.error,
    created_at: job.created_at,
    updated_at: job.updated_at,
  };
}

// ---------------------------------------------------------------- expediente

export function adaptDossier(res: DossierResultRaw, pipelineMs: number | null): Dossier {
  const all: Finding[] = res.findings.map((finding) => {
    const [category, ...rest] = finding.category.split("/");
    const inferred = finding.status === "inferred" || (finding.evidence.length > 0 && finding.evidence.every((e) => e.observed_or_inferred === "inferred"));
    return {
      id: finding.id,
      title: finding.title,
      category,
      subcategory: rest.join("/") || category,
      severity: SEVERITY[finding.severity],
      observed_or_inferred: inferred ? "inferred" : "observed",
      evidence: finding.evidence.map((e) => ({ path: e.path, line_start: e.line_start, line_end: e.line_end, snippet: e.fragment })),
      explanation: finding.explanation,
      recommendation: "",
      confidence: finding.confidence,
      priority: finding.priority,
      blast_radius_score: finding.blast_radius_score,
      verification_method: finding.verification_method,
      impacted_symbols: finding.transitive_impacted_symbols,
    };
  });
  const rejectedIds = new Set(res.findings.filter((f) => f.status === "rejected").map((f) => f.id));
  const findings = all.filter((f) => !rejectedIds.has(f.id));
  const rejected = all.filter((f) => rejectedIds.has(f.id));

  const checks: EvidenceCheck[] = all.flatMap((finding) =>
    finding.evidence.map((_, index) => ({
      finding_id: finding.id,
      evidence_index: index,
      status: rejectedIds.has(finding.id) ? ("invalid" as const) : ("valid" as const),
      reason: rejectedIds.has(finding.id)
        ? "El validador determinista no encontró el fragmento en ese rango"
        : "Validada por el validador determinista contra el archivo real",
    })),
  );

  const report = res.validation_report;
  return {
    schema_version: "1.0",
    execution_mode: res.execution_mode,
    repo_name: res.snapshot.repo_name,
    generated_at: res.snapshot.timestamp,
    bob_task_id: null,
    findings,
    rejected_findings: rejected,
    evidence_checks: checks,
    executive_summary: res.executive_summary,
    snapshot: { total_files: res.snapshot.total_files, total_loc: res.snapshot.total_loc, languages: res.snapshot.languages_detected, sha256: res.snapshot.snapshot_sha256 },
    stats: {
      findings_reported: res.findings.length,
      findings_validated: findings.length,
      evidence_total: report.total_references,
      evidence_valid: report.valid_references,
      evidence_valid_ratio: report.fidelity_ratio,
      bob_cost: null,
      bob_duration_ms: null,
      pipeline_ms: pipelineMs,
    },
  };
}

// ---------------------------------------------------------------- arquitectura

export function adaptArchitecture(res: DossierResultRaw): ArchitectureView {
  const diagrams: ArchitectureView["diagrams"] = [];
  if (res.mermaid_call_flow) diagrams.push({ id: "call-flow", label: "Flujo de llamadas (actual)", mermaid: res.mermaid_call_flow, provenance: "observed" });
  if (res.mermaid_er_diagram) diagrams.push({ id: "er", label: "Modelo de datos (actual)", mermaid: res.mermaid_er_diagram, provenance: "observed" });

  const migration = res.migration_summary;
  if (migration) {
    const modern = migration.modern_code_files[0] ?? "modern/";
    const endpoint = migration.endpoint_migrated.replace(/"/g, "'");
    diagrams.push({
      id: "target",
      label: "Objetivo tras el primer corte",
      provenance: "inferred",
      mermaid: `flowchart LR
  C(["Cliente"]):::observed --> F["${migration.facade_router_file}<br/>fachada Strangler Fig"]:::inferred
  F -->|"${endpoint}"| M["${modern}<br/>servicio FastAPI"]:::inferred
  F -->|"resto de rutas"| L["app.py<br/>Flask legado"]:::observed
  M --> DB[("SQLite")]:::observed
  L --> DB
  classDef observed fill:#0e3a4f,stroke:#38bdf8,color:#e6edf3,stroke-width:2px;
  classDef inferred fill:#2a2233,stroke:#c4a5ff,color:#e6edf3,stroke-dasharray:5 4;`,
    });
  }

  return {
    execution_mode: res.execution_mode,
    diagrams,
    selected_first_cut: res.selected_first_cut,
    options: res.architecture_options.map((option) => ({
      id: option.id,
      name: option.name,
      pattern: option.pattern,
      target_stack: option.target_stack,
      pros: option.pros,
      cons: option.cons,
      risk: option.risk_level.toLowerCase() as "low" | "medium" | "high",
      effort_days: option.estimated_effort_days,
      recommended: option.recommended,
    })),
    pert_plan: res.pert_plan.map((phase) => ({
      phase_number: phase.phase_number,
      name: phase.name,
      description: phase.description,
      optimistic_days: phase.optimistic_days,
      nominal_days: phase.nominal_days,
      pessimistic_days: phase.pessimistic_days,
      rollback_strategy: phase.rollback_strategy,
    })),
  };
}

// ---------------------------------------------------------------- migración

function testsFrom(report: TestReportRaw | null, suite: MigrationTest["suite"]): MigrationTest[] {
  return (report?.test_cases ?? []).map((test, index) => ({
    id: `${suite === "legacy" ? "L" : "M"}-${index + 1}`,
    name: test.name,
    status: TEST_STATUS[test.status],
    detail: [test.test_type, `${test.duration_ms.toFixed(1)} ms`, test.error_message].filter(Boolean).join(" · "),
    suite,
  }));
}

export async function adaptMigration(
  res: DossierResultRaw,
  jobId: string,
  fetchJson: <T>(path: string) => Promise<T>,
): Promise<MigrationView> {
  const migration = res.migration_summary;
  let legacy: MigrationView["legacy"] = null;
  let modern: MigrationView["modern"] = null;

  if (migration) {
    const modernPath = migration.modern_code_files[0];
    const slice = async (path: string, start: number, end: number) => {
      const query = new URLSearchParams({ path, start: String(start), end: String(end) });
      const data = await fetchJson<SourceExcerpt>(`/api/jobs/${encodeURIComponent(jobId)}/source?${query}`);
      return { path: data.path, code: data.lines.map((line) => line.text).join("\n"), line_start: data.start };
    };
    try {
      const graph = await fetchJson<GraphData>(`/api/jobs/${encodeURIComponent(jobId)}/graph`);
      const legacyNode = graph.nodes.find((node) => node.id === graph.migration_cut?.legacy_node);
      if (legacyNode) legacy = await slice(legacyNode.file, legacyNode.line_start, legacyNode.line_end);
    } catch {
      // sin grafo o sin sandbox: se muestra solo el lado que se pueda leer
    }
    if (modernPath) {
      try {
        modern = await slice(modernPath, 1, 400);
      } catch {
        modern = null;
      }
    }
  }

  const patch = migration?.diff_patch ?? "";
  return {
    execution_mode: res.execution_mode,
    slice_name: migration?.endpoint_migrated ?? res.selected_first_cut,
    description: migration
      ? `Primer corte Strangler Fig: ${migration.endpoint_migrated} sale del monolito hacia ${migration.modern_code_files.join(", ")} detrás de ${migration.facade_router_file}.`
      : "El pipeline no produjo un corte de migración para este análisis.",
    legacy,
    modern,
    tests: [...testsFrom(res.characterization_tests_legacy, "legacy"), ...testsFrom(res.characterization_tests_modern, "modern")],
    diff: migration
      ? {
          added: patch.split("\n").filter((line) => line.startsWith("+") && !line.startsWith("+++")).length,
          removed: patch.split("\n").filter((line) => line.startsWith("-") && !line.startsWith("---")).length,
        }
      : null,
    legacy_verdict: migration?.legacy_tests_verdict ?? null,
    modern_verdict: migration?.modern_tests_verdict ?? null,
  };
}

// ---------------------------------------------------------------- descargas

export function adaptDownloads(res: DossierResultRaw, jobId: string): DownloadsView {
  const base = `/api/jobs/${encodeURIComponent(jobId)}`;
  return {
    execution_mode: res.execution_mode,
    items: [
      { id: "docx", label: "Memo para la junta", description: "Riesgos, esfuerzo PERT y recomendación.", filename: "board_memo.docx", format: "DOCX", url: `${base}/artifacts/docx` },
      { id: "html", label: "Informe interactivo", description: "Expediente completo en una página HTML.", filename: "report.html", format: "HTML", url: `${base}/artifacts/html` },
      { id: "pptx", label: "Presentación ejecutiva", description: "Resumen en diapositivas para la junta.", filename: "presentation.pptx", format: "PPTX", url: `${base}/artifacts/pptx` },
      { id: "diff", label: "Parche de migración", description: "Diff unificado del primer corte Strangler Fig.", filename: "migration.diff", format: "DIFF", url: `${base}/artifacts/diff` },
      { id: "json", label: "Expediente (JSON)", description: "DossierResult completo conforme al contrato v1.", filename: "dossier.json", format: "JSON", url: `${base}/result` },
    ],
  };
}
