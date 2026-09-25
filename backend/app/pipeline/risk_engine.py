"""Motor Determinista de Radio de Explosión, Matriz de Riesgo y Estimación PERT (D-06).

Regla central de AGENTS.md: 'Los números los calcula código, no la IA'.
- Construye el grafo de llamadas con NetworkX.
- Calcula el Composite Blast Radius Score (CBRS) de 0 a 100.
- Evalúa la matriz determinista de riesgo (Impacto × Incertidumbre).
- Modela el plan de migración con distribución estadística PERT:
    E = (O + 4M + P) / 6,  Varianza = ((P - O) / 6)^2.
"""

import math
from pathlib import Path
from typing import Dict, List, Set, Tuple
import networkx as nx

from backend.app.models import Finding, MigrationPhase
from backend.app.pipeline.blast_radius import build_repository_call_graph


def calculate_finding_blast_radius(
    graph: nx.DiGraph,
    finding: Finding,
) -> Tuple[float, List[str]]:
    """Calcula el puntaje de radio de explosión transitivo (CBRS) para un hallazgo específico."""
    total_nodes = max(1, graph.number_of_nodes())
    impacted_nodes: Set[str] = set()

    # Identificar nodos raíz afectados a partir de la evidencia o símbolos
    seeds: Set[str] = set()
    for ev in finding.evidence:
        stem = Path(ev.path).stem
        for node in graph.nodes:
            if node.startswith(f"{stem}.") or f".{stem}." in node:
                seeds.add(node)

    for sym in finding.transitive_impacted_symbols:
        seeds.add(sym)

    for seed in seeds:
        if graph.has_node(seed):
            impacted_nodes.add(seed)
            # Impacto hacia arriba (quién me llama)
            callers = nx.ancestors(graph, seed)
            impacted_nodes.update(callers)
            # Impacto hacia abajo (a quién llamo)
            callees = nx.descendants(graph, seed)
            impacted_nodes.update(callees)

    impacted_count = len(impacted_nodes)
    ratio = impacted_count / total_nodes

    # Ponderación según severidad intrínseca
    severity_weight = {
        "CRITICAL": 1.25,
        "HIGH": 1.10,
        "MEDIUM": 0.95,
        "LOW": 0.80,
        "INFO": 0.60,
    }.get(finding.severity, 1.0)

    score = min(100.0, round(ratio * 100.0 * severity_weight, 1))
    if score == 0.0:
        # Fallback base según severidad si el grafo no tiene llamadas explícitas
        score = {"CRITICAL": 85.0, "HIGH": 65.0, "MEDIUM": 40.0, "LOW": 20.0, "INFO": 10.0}.get(finding.severity, 15.0)

    return score, sorted(list(impacted_nodes))


def enrich_findings_with_blast_radius(
    repo_dir: Path | str,
    findings: List[Finding],
) -> List[Finding]:
    """Enriquece cada hallazgo con su radio de impacto calculado en el grafo de llamadas."""
    graph = build_repository_call_graph(repo_dir)
    enriched = []
    for f in findings:
        score, symbols = calculate_finding_blast_radius(graph, f)
        f.blast_radius_score = score
        if not f.transitive_impacted_symbols:
            f.transitive_impacted_symbols = symbols[:8]  # Guardar los principales
        enriched.append(f)
    return enriched


def calculate_risk_matrix(findings: List[Finding]) -> Dict[str, Any]:
    """Genera la matriz de riesgo del repositorio: Impacto vs Incertidumbre."""
    severity_to_impact = {
        "CRITICAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "INFO": 1,
    }
    confidence_to_uncertainty = {
        "LOW": 5,
        "MEDIUM": 3,
        "HIGH": 1,
    }

    matrix_items = []
    total_risk_score = 0

    for f in findings:
        impact = severity_to_impact.get(f.severity, 3)
        uncertainty = confidence_to_uncertainty.get(f.confidence, 3)
        risk_score = impact * uncertainty
        total_risk_score += risk_score

        matrix_items.append({
            "finding_id": f.id,
            "title": f.title,
            "impact": impact,
            "uncertainty": uncertainty,
            "risk_score": risk_score,
            "category": f.category,
        })

    avg_risk = total_risk_score / max(1, len(findings))

    return {
        "total_findings": len(findings),
        "average_risk_score": round(avg_risk, 2),
        "risk_level": "HIGH" if avg_risk >= 12 else ("MEDIUM" if avg_risk >= 6 else "LOW"),
        "matrix": matrix_items,
    }


def generate_pert_migration_plan() -> List[MigrationPhase]:
    """Genera el plan de migración por fases con estimación probabilística PERT rigurosa."""
    raw_phases = [
        {
            "phase_number": 1,
            "name": "Fase 1: Harness de Caracterización y Contrato Inmutable",
            "description": "Estabilización de suite de pruebas de caracterización sobre FacturaYa heredado, fijación de Golden Master de GET /invoices/{id}, schemas Pydantic v2 y configuración del pipeline CI con SQLite en memoria.",
            "O": 2.0,
            "M": 3.5,
            "P": 6.0,
            "assumptions": [
                "El esquema de base de datos actual SQLite y los fixtures de clientes/facturas no sufrirán alteraciones.",
                "Se cuenta con cobertura de pruebas unitarias mínimas que reproduzcan el contrato actual sin alteraciones de red.",
            ],
            "prerequisites": ["Acceso de solo lectura al código heredado", "Ambiente de sandbox aislado"],
            "rollback_strategy": "Descarte de pruebas provisionales sin afectación a ningún entorno productivo.",
        },
        {
            "phase_number": 2,
            "name": "Fase 2: Primer Corte Strangler Fig (GET /invoices/{id})",
            "description": "Implementación del micro-módulo FastAPI para consulta de factura, consultas SQLite parametrizadas seguras, validación de pertenencia por propietario (BOLA fix) y enrutador fachada Strangler Fig.",
            "O": 3.0,
            "M": 5.0,
            "P": 9.0,
            "assumptions": [
                "La fachada Strangler Fig puede coexistir y redirigir el tráfico del endpoint GET /invoices/{id} sin latencia perceptible.",
                "Los clientes HTTP respetan el contrato JSON idéntico validado en la Fase 1.",
            ],
            "prerequisites": ["Pruebas de caracterización aprobadas al 100% en la Fase 1"],
            "rollback_strategy": "Cambio del switch de la fachada para redirigir 100% del tráfico al handler legacy Flask en menos de 1 segundo.",
        },
        {
            "phase_number": 3,
            "name": "Fase 3: Módulos Transaccionales y Reglas de Negocio",
            "description": "Migración de la ruta monolítica POST /invoices/new y resolución de la divergencia de redondeo en billing/reports mediante motor de descuentos unificado con tipado estricto Decimal.",
            "O": 5.0,
            "M": 8.0,
            "P": 14.0,
            "assumptions": [
                "Las partes interesadas financieras aprueban el redondeo bancario ROUND_HALF_UP por línea unificado.",
                "La base de datos soporta transacciones concurrentes con WAL mode.",
            ],
            "prerequisites": ["Fase 2 en producción estable sin incidencias de contrato"],
            "rollback_strategy": "Aislamiento de la transacción en el nuevo servicio y reintento de fallback a Flask mediante cola de compensación.",
        },
        {
            "phase_number": 4,
            "name": "Fase 4: Desmantelamiento del Monolito y Cutover Final",
            "description": "Retiro definitivo del servicio Flask heredado, eliminación de dependencias obsoletas, unificación de auditoría y monitoreo OpenTelemetry.",
            "O": 2.0,
            "M": 4.0,
            "P": 7.0,
            "assumptions": [
                "Todo el tráfico de producción ha sido redirigido al nuevo backend FastAPI durante al menos 14 días sin fallos.",
            ],
            "prerequisites": ["Cero dependencias activas del monolito Flask"],
            "rollback_strategy": "Restauración de la imagen del contenedor monolítico desde el registro de artefactos.",
        },
    ]

    phases: List[MigrationPhase] = []
    for rp in raw_phases:
        o = rp["O"]
        m = rp["M"]
        p = rp["P"]
        e = round((o + 4.0 * m + p) / 6.0, 2)
        variance = round(((p - o) / 6.0) ** 2, 4)

        phases.append(
            MigrationPhase(
                phase_number=rp["phase_number"],
                name=rp["name"],
                description=rp["description"],
                optimistic_days=o,
                nominal_days=m,
                pessimistic_days=p,
                pert_expected_days=e,
                pert_variance=variance,
                assumptions=rp["assumptions"],
                prerequisites=rp["prerequisites"],
                rollback_strategy=rp["rollback_strategy"],
            )
        )

    return phases


def calculate_total_pert_metrics(phases: List[MigrationPhase]) -> Dict[str, float]:
    """Calcula la duración esperada total y el intervalo de confianza al 95% (2 sigma)."""
    total_expected = sum(p.pert_expected_days for p in phases)
    total_variance = sum(p.pert_variance for p in phases)
    total_sigma = math.sqrt(total_variance)

    return {
        "total_expected_days": round(total_expected, 1),
        "total_variance": round(total_variance, 3),
        "total_sigma_days": round(total_sigma, 2),
        "confidence_95_min_days": round(max(0.0, total_expected - 2.0 * total_sigma), 1),
        "confidence_95_max_days": round(total_expected + 2.0 * total_sigma, 1),
    }
