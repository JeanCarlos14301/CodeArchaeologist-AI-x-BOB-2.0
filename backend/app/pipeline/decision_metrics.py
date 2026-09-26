"""Métricas deterministas para la decisión de migración.

No contiene salidas de IA: riesgo, impacto y PERT se derivan del expediente
validado y del análisis estático del workspace.
"""

import hashlib
import math
from pathlib import Path
from typing import Any

from app.contracts.schema_v1 import Dossier, PertEstimate, RiskMetric
from app.extractors.code_inventory import analyze_repository_inventory
from app.pipeline.callgraph import collect_functions, enclosing, resolve_edges

SEVERITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def source_sha256(workspace: Path) -> str:
    """Hash reproducible de rutas y bytes del código, excluyendo activos internos de Bob."""
    digest = hashlib.sha256()
    for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
        relative = path.relative_to(workspace)
        if ".bob" in relative.parts or "__pycache__" in relative.parts:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _origins(functions: list[dict[str, Any]], finding: Any) -> set[str]:
    result: set[str] = set()
    for evidence in finding.evidence:
        function = enclosing(functions, evidence.path, evidence.line_start, evidence.line_end)
        if function:
            result.add(function["id"])
    return result


def calculate_decision_metrics(workspace: Path, dossier: Dossier) -> tuple[list[RiskMetric], PertEstimate | None]:
    functions = collect_functions(workspace)
    edges = resolve_edges(functions)
    by_id = {function["id"]: function for function in functions}
    callers: dict[str, set[str]] = {}
    for edge in edges:
        callers.setdefault(edge["target"], set()).add(edge["source"])

    matrix: list[RiskMetric] = []
    impacts: dict[str, set[str]] = {}
    origins_by_finding: dict[str, set[str]] = {}
    for finding in dossier.findings:
        origins = _origins(functions, finding)
        impacted: set[str] = set()
        frontier = list(origins)
        while frontier:
            for caller in callers.get(frontier.pop(), set()):
                if caller not in origins and caller not in impacted:
                    impacted.add(caller)
                    frontier.append(caller)
        weight = SEVERITY_WEIGHT[finding.severity]
        score = weight * (1 + len(impacted))
        matrix.append(RiskMetric(
            finding_id=finding.id,
            severity_weight=weight,
            origin_functions=len(origins),
            impacted_callers=len(impacted),
            score=score,
            formula=f"{weight} × (1 + {len(impacted)} llamadores) = {score}",
        ))
        impacts[finding.id] = impacted
        origins_by_finding[finding.id] = origins

    if not matrix:
        return matrix, None

    first = max(matrix, key=lambda item: (item.score, item.severity_weight, item.finding_id))
    finding = next(item for item in dossier.findings if item.id == first.finding_id)
    affected_ids = origins_by_finding[first.finding_id] | impacts[first.finding_id]
    affected_functions = len(affected_ids)
    affected_routes = sum(1 for node_id in affected_ids if by_id.get(node_id, {}).get("route"))
    ranges = {(ev.path, ev.line_start, ev.line_end) for ev in finding.evidence}
    affected_lines = sum(end - start + 1 for _path, start, end in ranges)

    inventory = analyze_repository_inventory(workspace)
    affected_pairs = {(by_id[node_id]["file"], by_id[node_id]["name"]) for node_id in affected_ids if node_id in by_id}
    affected_complexity = sum(
        item.complexity for item in inventory.complex_functions
        if (item.file_path, item.function_name) in affected_pairs
    )

    points = (
        2 * affected_routes
        + affected_functions
        + math.ceil(affected_lines / 25)
        + math.ceil(affected_complexity / 5)
    )
    most_likely = round(max(1.0, points * 0.5), 1)
    optimistic = round(max(0.5, most_likely * 0.6), 1)
    pessimistic = round(max(most_likely, most_likely * 1.8), 1)
    expected = round((optimistic + 4 * most_likely + pessimistic) / 6, 2)
    variance = round(((pessimistic - optimistic) / 6) ** 2, 2)
    formula = (
        "M = (2×rutas + funciones + ceil(líneas/25) + ceil(complejidad/5)) × 0.5; "
        "O = 0.6×M; P = 1.8×M; E = (O + 4M + P) / 6"
    )
    estimate = PertEstimate(
        affected_routes=affected_routes,
        affected_functions=affected_functions,
        affected_lines=affected_lines,
        affected_complexity=affected_complexity,
        optimistic_days=optimistic,
        most_likely_days=most_likely,
        pessimistic_days=pessimistic,
        expected_days=expected,
        variance=variance,
        formula=formula,
        assumptions=[
            "Una persona desarrolladora familiarizada con Python, Flask, FastAPI y SQLite.",
            "Cada punto equivale a 0,5 días laborables e incluye implementación y pruebas del primer corte.",
            "El alcance se limita al hallazgo con mayor riesgo calculado y a sus llamadores transitivos.",
            "No incluye espera por aprobaciones, despliegue productivo ni migración de otros endpoints.",
        ],
    )
    return matrix, estimate
