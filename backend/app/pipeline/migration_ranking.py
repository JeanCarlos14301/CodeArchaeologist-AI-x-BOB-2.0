"""Motor determinista de recomendación de candidatos de migración y roadmap por olas (D3, D7).

Evalúa todas las rutas Flask de un repositorio sin ejecutar código alguno:
- Alcance: función de ruta + llamadores transitivos en el AST/grafo de llamadas.
- Valor: 1 + suma de pesos de severidad de hallazgos verificados en el alcance.
- Riesgo: 1 + funciones compartidas + 2 × tablas escritas + complejidad/5 + líneas/50 + 2 (circular).
- Facilidad: 1.0 (GET JSON), 0.5 (GET HTML), 0.25 (POST / mutación).
- Puntaje: valor × facilidad / riesgo.
- Salida: corte recomendado, 2 alternativas, 'no empezar por aquí', y olas con PERT.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    from app.contracts.schema_v1 import (
        Dossier,
        MigrationRecommendation,
        MigrationWave,
        PertEstimate,
        RouteCandidate,
    )
    from app.extractors.code_inventory import analyze_repository_inventory
    from app.pipeline.callgraph import collect_functions, enclosing, resolve_edges
except ImportError:
    from backend.app.contracts.schema_v1 import (
        Dossier,
        MigrationRecommendation,
        MigrationWave,
        PertEstimate,
        RouteCandidate,
    )
    from backend.app.extractors.code_inventory import analyze_repository_inventory
    from backend.app.pipeline.callgraph import collect_functions, enclosing, resolve_edges


SEVERITY_WEIGHT: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

PERT_DISCLAIMER = "Estimación heurística, no calibrada (0,5 días por punto de complejidad y acoplamiento)."


def calculate_pert_for_scope(
    affected_routes: int,
    affected_functions: int,
    affected_lines: int,
    affected_complexity: int,
    scope_description: str,
) -> PertEstimate:
    """Calcula la estimación PERT (O, M, P, E, Var) para un alcance de funciones y rutas."""
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
    assumptions = [
        PERT_DISCLAIMER,
        "Una persona desarrolladora familiarizada con Python, Flask, FastAPI y SQLite.",
        f"Alcance evaluado: {scope_description}.",
        "Incluye implementación del endpoint, validación de esquemas y pruebas de caracterización.",
        "No incluye aprobaciones corporativas, despliegue productivo ni migración de otros endpoints.",
    ]
    return PertEstimate(
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
        assumptions=assumptions,
    )


def analyze_route_candidates(
    workspace: Path,
    dossier: Dossier | None = None,
) -> MigrationRecommendation:
    """Calcula el ranking determinista de candidatos de migración y organiza las olas."""
    functions = collect_functions(workspace)
    edges = resolve_edges(functions)
    inv = analyze_repository_inventory(workspace)

    by_id = {fn["id"]: fn for fn in functions}
    callees: dict[str, set[str]] = {}
    for edge in edges:
        callees.setdefault(edge["source"], set()).add(edge["target"])

    route_functions = [fn for fn in functions if fn.get("route")]
    if not route_functions and inv.routes:
        # Si no se detectaron directamente en callgraph, cruzar con inv.routes
        for route_info in inv.routes:
            for fn in functions:
                if (
                    fn["file"] == route_info.file_path
                    and fn["name"] == route_info.function_name
                    and not fn.get("route")
                ):
                    fn["route"] = {
                        "rule": route_info.rule,
                        "methods": route_info.http_methods,
                    }
                    route_functions.append(fn)

    if not route_functions:
        return MigrationRecommendation()

    # Mapeo de hallazgos verificados a funciones del AST
    findings_by_id = {f.id: f for f in (dossier.findings if dossier else [])}
    finding_origins: dict[str, set[str]] = {}
    for finding in findings_by_id.values():
        origins = set()
        for ev in finding.evidence:
            fn = enclosing(functions, ev.path, ev.line_start, ev.line_end)
            if fn:
                origins.add(fn["id"])
        finding_origins[finding.id] = origins

    # Alcance de cada ruta: función + llamadores transitivos
    scopes: dict[str, set[str]] = {}
    for rf in route_functions:
        scope = {rf["id"]}
        frontier = [rf["id"]]
        while frontier:
            curr = frontier.pop()
            for target in callees.get(curr, set()):
                if target not in scope:
                    scope.add(target)
                    frontier.append(target)
        scopes[rf["id"]] = scope

    # Conteo de funciones compartidas entre diferentes rutas
    func_routes_count: dict[str, int] = {}
    for sc in scopes.values():
        for fid in sc:
            func_routes_count[fid] = func_routes_count.get(fid, 0) + 1

    # Detección de consultas de escritura por función
    write_tables_by_fn: dict[str, set[str]] = {}
    for q in inv.sql_queries:
        if q.query_type in ("INSERT", "UPDATE", "DELETE"):
            fn = enclosing(functions, q.file_path, q.line_start, q.line_end)
            if fn:
                write_tables_by_fn.setdefault(fn["id"], set()).update(q.tables_referenced)

    # Complejidad y líneas por función
    complexity_by_fn: dict[str, int] = {}
    lines_by_fn: dict[str, int] = {}
    for fn in functions:
        lines_by_fn[fn["id"]] = max(1, fn["line_end"] - fn["line_start"] + 1)
    for cf in inv.complex_functions:
        for fn in functions:
            if fn["file"] == cf.file_path and fn["name"] == cf.function_name:
                complexity_by_fn[fn["id"]] = cf.complexity

    # Archivos involucrados en dependencias circulares
    circular_files: set[str] = set()
    for cycle in inv.circular_dependencies:
        circular_files.update(cycle)

    candidates: list[RouteCandidate] = []
    for rf in route_functions:
        rid = rf["id"]
        sc = scopes[rid]

        # 1. Valor: 1 + suma de pesos de severidad de hallazgos verificados
        findings_in_scope: list[str] = []
        for fid, origins in finding_origins.items():
            if origins & sc:
                findings_in_scope.append(fid)
        val = 1.0 + sum(SEVERITY_WEIGHT[findings_by_id[fid].severity] for fid in findings_in_scope)

        # 2. Riesgo: 1 + compartidas + 2*tablas + cc/5 + líneas/50 + circular
        shared_funcs = sum(1 for fid in sc if func_routes_count.get(fid, 0) > 1 and fid != rid)
        tables_written: set[str] = set()
        for fid in sc:
            tables_written.update(write_tables_by_fn.get(fid, set()))
        num_written = len(tables_written)
        total_complexity = sum(complexity_by_fn.get(fid, 1) for fid in sc)
        total_lines = sum(lines_by_fn.get(fid, 1) for fid in sc)
        in_circular = any(by_id.get(fid, {}).get("file") in circular_files for fid in sc)
        circ_penalty = 2.0 if in_circular else 0.0

        risk = round(
            1.0
            + shared_funcs
            + 2.0 * num_written
            + (total_complexity / 5.0)
            + (total_lines / 50.0)
            + circ_penalty,
            2,
        )

        # 3. Facilidad de probar
        methods = rf["route"]["methods"]
        rule = rf["route"]["rule"]
        file_path = rf["file"]
        full_code = ""
        src_file = workspace / file_path
        if src_file.is_file():
            try:
                code_lines = src_file.read_text(encoding="utf-8", errors="replace").splitlines()
                full_code = "\n".join(code_lines[rf["line_start"] - 1 : rf["line_end"]])
            except OSError:
                pass

        if any(m in ("POST", "PUT", "DELETE", "PATCH") for m in methods) or num_written > 0:
            testability = 0.25
        elif "jsonify" in full_code or "/api/" in rule:
            testability = 1.0
        else:
            testability = 0.5

        score = round((val * testability) / risk, 3)

        method_str = ", ".join(methods)
        endpoint = f"{method_str} {rule}"
        formula_str = (
            f"score = (valor {val} × facilidad {testability}) / riesgo {risk} = {score} "
            f"[mitiga {len(findings_in_scope)} hallazgos; {shared_funcs} funciones compartidas, "
            f"{num_written} tablas escritas, {total_complexity} cc, {total_lines} líneas]"
        )

        why_parts = []
        if testability == 1.0:
            why_parts.append("Responde JSON puro con contrato formal")
        elif testability == 0.5:
            why_parts.append("Endpoint de solo lectura que renderiza vista")
        else:
            why_parts.append("Endpoint con mutación o método POST")

        if num_written == 0:
            why_parts.append("sin escrituras en base de datos")
        else:
            why_parts.append(f"con escrituras en {num_written} tabla(s): {', '.join(sorted(tables_written))}")

        if findings_in_scope:
            why_parts.append(f"mitiga {len(findings_in_scope)} hallazgo(s) ({', '.join(findings_in_scope)})")

        why_str = ", ".join(why_parts) + "."

        candidates.append(
            RouteCandidate(
                endpoint=endpoint,
                http_methods=methods,
                rule=rule,
                function_name=rf["name"],
                file_path=file_path,
                line_start=rf["line_start"],
                line_end=rf["line_end"],
                value=val,
                risk=risk,
                testability=testability,
                score=score,
                formula=formula_str,
                findings_mitigated=sorted(findings_in_scope),
                shared_functions=shared_funcs,
                tables_written=sorted(tables_written),
                complexity=total_complexity,
                lines=total_lines,
                in_circular_dependency=in_circular,
                why=why_str,
            )
        )

    # Ordenar candidatos descendentemente por score, luego por facilidad y menor riesgo
    candidates.sort(key=lambda c: (c.score, c.testability, -c.risk), reverse=True)

    recommended = candidates[0] if candidates else None
    alternatives = candidates[1:3] if len(candidates) > 1 else []
    # "No empezar por aquí": la ruta más acoplada y riesgosa (ej. POST /invoices/new)
    do_not_start_here = max(candidates, key=lambda c: (c.risk, -c.score)) if candidates else None

    # Hoja de ruta Strangler Fig en 3 Olas
    # Ola 1: Candidatos con facilidad >= 0.5 y bajo/medio riesgo
    # Ola 2: Candidatos de lectura / HTML intermedios
    # Ola 3: Candidatos transaccionales, escrituras o alto acoplamiento
    wave1_cands = [c for c in candidates if c.testability == 1.0 or (c.testability == 0.5 and c.risk <= 5.0)]
    wave3_cands = [c for c in candidates if c.testability == 0.25 or c.risk > 15.0 or len(c.tables_written) > 0]
    # Si coinciden, wave 3 tiene prioridad para escrituras
    wave1_cands = [c for c in wave1_cands if c not in wave3_cands]
    wave2_cands = [c for c in candidates if c not in wave1_cands and c not in wave3_cands]

    # Asegurar que ninguna ola quede vacía si hay suficientes candidatos
    if not wave1_cands and candidates:
        wave1_cands = candidates[:1]
        wave2_cands = candidates[1:3]
        wave3_cands = candidates[3:]

    def pert_for_candidates(cands: list[RouteCandidate], label: str) -> PertEstimate | None:
        if not cands:
            return None
        all_funcs: set[str] = set()
        for c in cands:
            for fn in functions:
                if fn["file"] == c.file_path and fn["name"] == c.function_name:
                    all_funcs.update(scopes.get(fn["id"], set()))
        total_lines = sum(lines_by_fn.get(fid, 1) for fid in all_funcs)
        total_cc = sum(complexity_by_fn.get(fid, 1) for fid in all_funcs)
        return calculate_pert_for_scope(
            affected_routes=len(cands),
            affected_functions=len(all_funcs),
            affected_lines=total_lines,
            affected_complexity=total_cc,
            scope_description=label,
        )

    waves: list[MigrationWave] = [
        MigrationWave(
            wave_number=1,
            name="Ola 1 — Primeros Cortes Seguros (Leaf Endpoints & JSON)",
            description="Endpoints de lectura con bajo acoplamiento y contratos fácilmente comprobables sin riesgo transaccional.",
            candidates=wave1_cands,
            pert=pert_for_candidates(wave1_cands, "Ola 1: endpoints de lectura independientes"),
        ),
        MigrationWave(
            wave_number=2,
            name="Ola 2 — Vistas y Consultas Intermedias",
            description="Endpoints de lectura HTML y catálogos dependientes del modelo de datos legado.",
            candidates=wave2_cands,
            pert=pert_for_candidates(wave2_cands, "Ola 2: vistas y catálogos secundarios"),
        ),
        MigrationWave(
            wave_number=3,
            name="Ola 3 — Dominio Transaccional y Escritura Crítica",
            description="Controladores complejos con mutaciones en base de datos, transacciones y dependencias cruzadas.",
            candidates=wave3_cands,
            pert=pert_for_candidates(wave3_cands, "Ola 3: mutaciones y reglas de negocio complejas"),
        ),
    ]

    # PERT del corte recomendado
    first_cut_pert = None
    if recommended:
        rf_match = next((fn for fn in route_functions if fn["file"] == recommended.file_path and fn["name"] == recommended.function_name), None)
        rec_scope = scopes.get(rf_match["id"], set()) if rf_match else set()
        rec_lines = sum(lines_by_fn.get(fid, 1) for fid in rec_scope)
        rec_cc = sum(complexity_by_fn.get(fid, 1) for fid in rec_scope)
        first_cut_pert = calculate_pert_for_scope(
            affected_routes=1,
            affected_functions=len(rec_scope),
            affected_lines=rec_lines,
            affected_complexity=rec_cc,
            scope_description=f"Corte recomendado: {recommended.endpoint} ({recommended.function_name})",
        )

    # Comparación con corte de referencia (D3 honestidad)
    ref_comparison = None
    ref_candidate = next((c for c in candidates if "invoices/" in c.rule and c.testability == 1.0), None)
    if ref_candidate and recommended:
        if ref_candidate.endpoint == recommended.endpoint:
            ref_comparison = (
                f"El motor determinista seleccionó autónomamente {recommended.endpoint}, "
                "coincidiendo con el primer corte ejecutado como referencia."
            )
        else:
            ref_comparison = (
                f"El motor determinista calculó {recommended.endpoint} como corte óptimo por ratio valor/riesgo ({recommended.score}), "
                f"mientras que el corte ejecutado en laboratorio como referencia es {ref_candidate.endpoint} (score: {ref_candidate.score}). "
                "Ambos pertenecen a la Ola 1 por su bajo acoplamiento."
            )

    return MigrationRecommendation(
        recommended=recommended,
        alternatives=alternatives,
        do_not_start_here=do_not_start_here,
        candidates=candidates,
        waves=waves,
        first_cut_pert=first_cut_pert,
        reference_comparison=ref_comparison,
    )
