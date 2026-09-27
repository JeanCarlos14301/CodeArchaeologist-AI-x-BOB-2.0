"""Deterministic blast radius, risk matrix and PERT estimation engine (D-06; not wired into the product).

Central AGENTS.md rule: 'Numbers are computed by code, not by the AI'.
- Builds the call graph with NetworkX.
- Computes the Composite Blast Radius Score (CBRS) from 0 to 100.
- Evaluates the deterministic risk matrix (Impact × Uncertainty).
- Models the migration plan with the PERT statistical distribution:
    E = (O + 4M + P) / 6,  Variance = ((P - O) / 6)^2.
"""

import math
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import networkx as nx

from backend.app.models import Finding, MigrationPhase
from backend.app.pipeline.blast_radius import build_repository_call_graph


def calculate_finding_blast_radius(
    graph: nx.DiGraph,
    finding: Finding,
) -> Tuple[float, List[str]]:
    """Computes the transitive blast radius score (CBRS) for a specific finding."""
    total_nodes = max(1, graph.number_of_nodes())
    impacted_nodes: Set[str] = set()

    # Identify the affected root nodes from the evidence or the symbols
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
            # Upstream impact (who calls me)
            callers = nx.ancestors(graph, seed)
            impacted_nodes.update(callers)
            # Downstream impact (whom I call)
            callees = nx.descendants(graph, seed)
            impacted_nodes.update(callees)

    impacted_count = len(impacted_nodes)
    ratio = impacted_count / total_nodes

    # Weighting by intrinsic severity
    severity_weight = {
        "CRITICAL": 1.25,
        "HIGH": 1.10,
        "MEDIUM": 0.95,
        "LOW": 0.80,
        "INFO": 0.60,
    }.get(finding.severity, 1.0)

    score = min(100.0, round(ratio * 100.0 * severity_weight, 1))
    if score == 0.0:
        # Base fallback by severity when the graph has no explicit calls
        score = {"CRITICAL": 85.0, "HIGH": 65.0, "MEDIUM": 40.0, "LOW": 20.0, "INFO": 10.0}.get(finding.severity, 15.0)

    return score, sorted(list(impacted_nodes))


def enrich_findings_with_blast_radius(
    repo_dir: Path | str,
    findings: List[Finding],
) -> List[Finding]:
    """Enriches each finding with its blast radius computed on the call graph."""
    graph = build_repository_call_graph(repo_dir)
    enriched = []
    for f in findings:
        score, symbols = calculate_finding_blast_radius(graph, f)
        f.blast_radius_score = score
        if not f.transitive_impacted_symbols:
            f.transitive_impacted_symbols = symbols[:8]  # Keep the main ones
        enriched.append(f)
    return enriched


def calculate_risk_matrix(findings: List[Finding]) -> Dict[str, Any]:
    """Builds the repository risk matrix: Impact vs Uncertainty."""
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
    """Builds the phased migration plan with a rigorous probabilistic PERT estimate."""
    raw_phases = [
        {
            "phase_number": 1,
            "name": "Phase 1: Characterization harness and immutable contract",
            "description": "Stabilize the characterization test suite on legacy FacturaYa, pin the GET /invoices/{id} golden master, Pydantic v2 schemas and a CI pipeline with in-memory SQLite.",
            "O": 2.0,
            "M": 3.5,
            "P": 6.0,
            "assumptions": [
                "The current SQLite schema and the customer/invoice fixtures will not change.",
                "Minimal unit test coverage exists that reproduces the current contract without network changes.",
            ],
            "prerequisites": ["Read-only access to the legacy code", "Isolated sandbox environment"],
            "rollback_strategy": "Discard the provisional tests with no effect on any production environment.",
        },
        {
            "phase_number": 2,
            "name": "Phase 2: First Strangler Fig cut (GET /invoices/{id})",
            "description": "Implement the FastAPI micro-module for invoice lookup, safe parameterized SQLite queries, owner validation (BOLA fix) and the Strangler Fig facade router.",
            "O": 3.0,
            "M": 5.0,
            "P": 9.0,
            "assumptions": [
                "The Strangler Fig facade can coexist with and route traffic for GET /invoices/{id} with no noticeable latency.",
                "HTTP clients honor the identical JSON contract validated in Phase 1.",
            ],
            "prerequisites": ["Characterization tests passing 100% in Phase 1"],
            "rollback_strategy": "Flip the facade switch to send 100% of traffic back to the legacy Flask handler in under 1 second.",
        },
        {
            "phase_number": 3,
            "name": "Phase 3: Transactional modules and business rules",
            "description": "Migrate the monolithic POST /invoices/new route and resolve the rounding divergence in billing/reports with a unified discount engine using strict Decimal typing.",
            "O": 5.0,
            "M": 8.0,
            "P": 14.0,
            "assumptions": [
                "Financial stakeholders approve unified per-line ROUND_HALF_UP banker's rounding.",
                "The database supports concurrent transactions with WAL mode.",
            ],
            "prerequisites": ["Phase 2 stable in production with no contract incidents"],
            "rollback_strategy": "Isolate the transaction in the new service and fall back to Flask through a compensation queue.",
        },
        {
            "phase_number": 4,
            "name": "Phase 4: Monolith decommissioning and final cutover",
            "description": "Retire the legacy Flask service for good, remove obsolete dependencies, unify auditing and OpenTelemetry monitoring.",
            "O": 2.0,
            "M": 4.0,
            "P": 7.0,
            "assumptions": [
                "All production traffic has been routed to the new FastAPI backend for at least 14 days without failures.",
            ],
            "prerequisites": ["Zero active dependencies on the Flask monolith"],
            "rollback_strategy": "Restore the monolith container image from the artifact registry.",
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
    """Computes the total expected duration and the 95% confidence interval (2 sigma)."""
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
