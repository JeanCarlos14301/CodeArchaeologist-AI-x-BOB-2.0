import dossierExample from "../../../contracts/fixtures/dossier-example.json";
import type { ArchitectureView, Dossier, DownloadsView, Job, MigrationView } from "../types";

// Datos de ejemplo (execution_mode: "example"). Solo se usan si la API no responde
// o aún no expone el endpoint correspondiente.

export const EXAMPLE_DOSSIER = dossierExample as unknown as Dossier;

export const EXAMPLE_JOB: Job = {
  id: "demo-fixture",
  sample: "facturaya-v1",
  execution_mode: "example",
  status: "done",
  stage: "done",
  error: null,
  created_at: EXAMPLE_DOSSIER.generated_at,
  updated_at: EXAMPLE_DOSSIER.generated_at,
};

const MERMAID_STYLES = `
  classDef observed fill:#0e3a4f,stroke:#38bdf8,color:#e6edf3,stroke-width:2px;
  classDef inferred fill:#2a2233,stroke:#c4a5ff,color:#e6edf3,stroke-dasharray:5 4;`;

export const EXAMPLE_ARCHITECTURE: ArchitectureView = {
  execution_mode: "example",
  selected_first_cut: "GET /invoices/{id}",
  diagrams: [
    {
      id: "current",
      label: "Arquitectura actual",
      provenance: "observed",
      mermaid: `flowchart LR
  U(["Usuario"]):::observed --> APP["app.py<br/>rutas Flask"]:::observed
  APP --> BIL["billing.py<br/>facturación + descuento"]:::observed
  APP --> CUS["customers.py"]:::observed
  APP --> REP["reports.py<br/>descuento duplicado"]:::observed
  CUS <-->|"import circular"| BIL
  BIL --> DB[("SQLite<br/>columnas TEXT")]:::observed
  REP --> DB
  CUS --> DB
  CFG["config.py<br/>secretos en claro"]:::observed --> APP${MERMAID_STYLES}`,
    },
    {
      id: "target",
      label: "Arquitectura objetivo",
      provenance: "inferred",
      mermaid: `flowchart LR
  U(["Usuario"]):::observed --> GW["Fachada Strangler<br/>enruta legado / nuevo"]:::inferred
  GW -->|"rutas migradas"| API["FastAPI<br/>servicio de facturación"]:::inferred
  GW -->|"resto"| LEG["Flask legado"]:::observed
  API --> PRC["pricing<br/>regla única de descuento"]:::inferred
  LEG --> DB[("SQLite")]:::observed
  API --> DB${MERMAID_STYLES}`,
    },
  ],
  options: [
    {
      id: "strangler",
      name: "Strangler Fig por módulos",
      pattern: "Strangler Fig",
      target_stack: "FastAPI",
      pros: ["Entrega valor incremental", "El legado sigue en producción", "Cada corte se prueba de forma aislada"],
      cons: ["Convivencia temporal de dos stacks", "Requiere una fachada de enrutamiento"],
      risk: "low",
      effort_days: 11,
      recommended: true,
    },
    {
      id: "big-bang",
      name: "Reescritura completa",
      pattern: "Big Bang",
      target_stack: "FastAPI",
      pros: ["Diseño limpio desde cero"],
      cons: ["Sin pruebas previas que garanticen equivalencia", "Riesgo alto en el corte final"],
      risk: "high",
      effort_days: 32,
      recommended: false,
    },
    {
      id: "harden",
      name: "Endurecer y refactorizar in situ",
      pattern: "Refactor",
      target_stack: "Flask",
      pros: ["Menor esfuerzo inmediato", "Sin nuevo stack"],
      cons: ["La deuda de fondo permanece", "No resuelve la ausencia de pruebas"],
      risk: "medium",
      effort_days: 6,
      recommended: false,
    },
  ],
  pert_plan: [
    { phase_number: 1, name: "Harness de caracterización", description: "Fijar el comportamiento observable antes de tocar código.", optimistic_days: 2, nominal_days: 3.5, pessimistic_days: 6, rollback_strategy: "Descartar las pruebas provisionales." },
    { phase_number: 2, name: "Primer corte Strangler", description: "Extraer el endpoint elegido a FastAPI tras una fachada.", optimistic_days: 3, nominal_days: 5, pessimistic_days: 9, rollback_strategy: "Apuntar la fachada de nuevo al legado." },
  ],
};

export const EXAMPLE_MIGRATION: MigrationView = {
  execution_mode: "example",
  slice_name: "Cálculo de descuento",
  description:
    "Primer corte Strangler Fig: la regla de descuento (F-4) vive duplicada en billing.py y reports.py. Se extrae a un único servicio.",
  legacy: {
    path: "billing.py",
    line_start: 6,
    code: `RATE = Decimal("0.075")
THRESHOLD = Decimal("100.00")

def calculate(items):
    subtotal = sum(Decimal(str(i["line_total"])) for i in items)
    discount = (subtotal * RATE).quantize(CENT, rounding=ROUND_HALF_UP) \\
        if subtotal >= THRESHOLD else Decimal("0.00")
    return subtotal, discount, subtotal - discount`,
  },
  modern: {
    path: "pricing/discount.py",
    line_start: 1,
    code: `from decimal import ROUND_HALF_UP, Decimal

RATE = Decimal("0.075")
THRESHOLD = Decimal("100.00")
CENT = Decimal("0.01")


def calculate_discount(subtotal: Decimal) -> Decimal:
    """Única fuente de verdad de la regla de descuento."""
    if subtotal < THRESHOLD:
        return Decimal("0.00")
    return (subtotal * RATE).quantize(CENT, rounding=ROUND_HALF_UP)`,
  },
  tests: [
    { id: "T-1", suite: "legacy", name: "Sin descuento bajo el umbral", status: "passed", detail: "subtotal 99.99 → 0.00" },
    { id: "T-2", suite: "legacy", name: "Descuento en el umbral exacto", status: "passed", detail: "subtotal 100.00 → 7.50" },
    { id: "T-3", suite: "modern", name: "Redondeo half-up", status: "passed", detail: "subtotal 133.33 → 10.00" },
    { id: "T-4", suite: "modern", name: "Reporte coincide con factura", status: "failed", detail: "reports.py difiere en 0.01 por redondeo por ítem" },
    { id: "T-5", suite: "modern", name: "Equivalencia con la base completa", status: "not_run", detail: "Requiere la base de datos del legado" },
  ],
  diff: null,
  legacy_verdict: null,
  modern_verdict: null,
};

export const EXAMPLE_DOWNLOADS: DownloadsView = {
  execution_mode: "example",
  items: [
    { id: "memo", label: "Memo para la junta", description: "Riesgos, esfuerzo PERT y recomendación en DOCX.", filename: "memo-junta.docx", format: "DOCX", url: null },
    { id: "dossier", label: "Expediente técnico", description: "Hallazgos con evidencia por archivo y línea.", filename: "expediente.json", format: "JSON", url: null },
    { id: "migration", label: "Primer corte de migración", description: "Código nuevo y pruebas del corte Strangler Fig.", filename: "migracion.zip", format: "ZIP", url: null },
  ],
};
