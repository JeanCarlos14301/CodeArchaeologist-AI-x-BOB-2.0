"""Deterministic engine that ranks migration candidates and builds the roadmap by waves (D3, D7).

Scores every Flask route of a repository without running any code:
- Scope: route function + the functions it calls, directly or transitively (AST call graph).
- Value: 1 + sum of the severity weights of the verified findings in the scope.
- Risk: 1 + shared functions + 2 × written tables + complexity/5 + lines/50 + 2 (circular).
- Testability: 1.0 (GET JSON), 0.5 (GET HTML), 0.25 (POST / mutation).
- Business data: 1.0 when the scope reads or writes any table; 0.5 otherwise (D3: visible to the business).
- Score: value × testability × business data / risk.
- Output: recommended cut, 2 alternatives, 'do not start here', and waves with PERT.
"""

from __future__ import annotations

import math
import re
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

PERT_DISCLAIMER = "Uncalibrated heuristic estimate (0.5 days per point of complexity and coupling)."


def calculate_pert_for_scope(
    affected_routes: int,
    affected_functions: int,
    affected_lines: int,
    affected_complexity: int,
    scope_description: str,
) -> PertEstimate:
    """Computes the PERT estimate (O, M, P, E, Var) for a scope of functions and routes."""
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
        "M = (2×routes + functions + ceil(lines/25) + ceil(complexity/5)) × 0.5; "
        "O = 0.6×M; P = 1.8×M; E = (O + 4M + P) / 6"
    )
    assumptions = [
        PERT_DISCLAIMER,
        "One developer familiar with Python, Flask, FastAPI and SQLite.",
        f"Scope assessed: {scope_description}.",
        "Includes implementing the endpoint, schema validation and characterization tests.",
        "Excludes corporate approvals, production deployment and migrating other endpoints.",
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
    """Computes the deterministic ranking of migration candidates and organizes the waves."""
    functions = collect_functions(workspace)
    edges = resolve_edges(functions)
    inv = analyze_repository_inventory(workspace)

    by_id = {fn["id"]: fn for fn in functions}
    callees: dict[str, set[str]] = {}
    for edge in edges:
        callees.setdefault(edge["source"], set()).add(edge["target"])

    route_functions = [fn for fn in functions if fn.get("route")]
    if not route_functions and inv.routes:
        # If they were not detected directly in the call graph, cross-check with inv.routes
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

    # Map verified findings to AST functions
    findings_by_id = {f.id: f for f in (dossier.findings if dossier else [])}
    finding_origins: dict[str, set[str]] = {}
    for finding in findings_by_id.values():
        origins = set()
        for ev in finding.evidence:
            fn = enclosing(functions, ev.path, ev.line_start, ev.line_end)
            if fn:
                origins.add(fn["id"])
        finding_origins[finding.id] = origins

    # Scope of each route: function + the functions it calls transitively
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

    # Count of functions shared between different routes
    func_routes_count: dict[str, int] = {}
    for sc in scopes.values():
        for fid in sc:
            func_routes_count[fid] = func_routes_count.get(fid, 0) + 1

    # Detection of write queries per function, and of any table touched (read or write)
    write_tables_by_fn: dict[str, set[str]] = {}
    touched_tables_by_fn: dict[str, set[str]] = {}
    for q in inv.sql_queries:
        fn = enclosing(functions, q.file_path, q.line_start, q.line_end)
        if not fn:
            continue
        touched_tables_by_fn.setdefault(fn["id"], set()).update(q.tables_referenced)
        if q.query_type in ("INSERT", "UPDATE", "DELETE"):
            write_tables_by_fn.setdefault(fn["id"], set()).update(q.tables_referenced)

    # Complexity and lines per function
    complexity_by_fn: dict[str, int] = {}
    lines_by_fn: dict[str, int] = {}
    for fn in functions:
        lines_by_fn[fn["id"]] = max(1, fn["line_end"] - fn["line_start"] + 1)
    for cf in inv.complex_functions:
        for fn in functions:
            if fn["file"] == cf.file_path and fn["name"] == cf.function_name:
                complexity_by_fn[fn["id"]] = cf.complexity

    # Files involved in circular dependencies
    circular_files: set[str] = set()
    for cycle in inv.circular_dependencies:
        circular_files.update(cycle)

    candidates: list[RouteCandidate] = []
    for rf in route_functions:
        rid = rf["id"]
        sc = scopes[rid]

        # 1. Value: 1 + sum of the severity weights of verified findings
        findings_in_scope: list[str] = []
        for fid, origins in finding_origins.items():
            if origins & sc:
                findings_in_scope.append(fid)
        val = 1.0 + sum(SEVERITY_WEIGHT[findings_by_id[fid].severity] for fid in findings_in_scope)

        # 2. Risk: 1 + shared + 2*tables + cc/5 + lines/50 + circular
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

        # 3. Testability
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

        # 4. Business data: a route that touches no table (logout, index) is not a meaningful first cut,
        # even if it is tiny and happens to hold the evidence line of a cross-cutting finding.
        touches_data = any(touched_tables_by_fn.get(fid) for fid in sc)
        business_factor = 1.0 if touches_data else 0.5

        score = round((val * testability * business_factor) / risk, 3)

        method_str = ", ".join(methods)
        endpoint = f"{method_str} {rule}"
        formula_str = (
            f"score = (value {val} × testability {testability} × data {business_factor}) / risk {risk} = {score} "
            f"[mitigates {len(findings_in_scope)} findings; {shared_funcs} shared functions, "
            f"{num_written} written tables, {total_complexity} cc, {total_lines} lines]"
        )

        why_parts = []
        if testability == 1.0:
            why_parts.append("Returns pure JSON with a formal contract")
        elif testability == 0.5:
            why_parts.append("Read-only endpoint that renders a view")
        else:
            why_parts.append("Endpoint with a mutation or a POST method")

        if num_written == 0:
            why_parts.append("no database writes")
        else:
            why_parts.append(f"writes to {num_written} table(s): {', '.join(sorted(tables_written))}")

        if not touches_data:
            why_parts.append("reads and writes no business data (score halved)")

        if findings_in_scope:
            why_parts.append(f"mitigates {len(findings_in_scope)} finding(s) ({', '.join(findings_in_scope)})")

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
                touches_business_data=touches_data,
                why=why_str,
            )
        )

    # Sort candidates by score descending, then by testability and lower risk
    candidates.sort(key=lambda c: (c.score, c.testability, -c.risk), reverse=True)

    recommended = candidates[0] if candidates else None
    alternatives = candidates[1:3] if len(candidates) > 1 else []
    # "Do not start here": the most coupled and risky route (e.g. POST /invoices/new)
    do_not_start_here = max(candidates, key=lambda c: (c.risk, -c.score)) if candidates else None

    # Strangler Fig roadmap in 3 waves
    # Wave 1: candidates with testability >= 0.5 and low/medium risk
    # Wave 2: intermediate read / HTML candidates
    # Wave 3: transactional candidates, writes or high coupling
    wave1_cands = [c for c in candidates if c.testability == 1.0 or (c.testability == 0.5 and c.risk <= 5.0)]
    wave3_cands = [c for c in candidates if c.testability == 0.25 or c.risk > 15.0 or len(c.tables_written) > 0]
    # When both apply, wave 3 wins for writes
    wave1_cands = [c for c in wave1_cands if c not in wave3_cands]
    wave2_cands = [c for c in candidates if c not in wave1_cands and c not in wave3_cands]

    # Make sure no wave is empty when there are enough candidates
    by_rank = False
    if not wave1_cands and candidates:
        # No read-only, low-coupling route exists: waves follow the ranking instead of the route kind,
        # and their names say so rather than promising "safe read endpoints".
        by_rank = True
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

    if by_rank:
        wave_text = [
            ("Wave 1 — Best available candidate",
             "There are no low-coupling read-only endpoints: start with the highest-scoring route.",
             "Wave 1: highest-scoring route"),
            ("Wave 2 — Next in the ranking",
             "The next two routes by ranking score.",
             "Wave 2: next routes in the ranking"),
            ("Wave 3 — Remaining routes",
             "Remaining, lower-scoring routes.",
             "Wave 3: remaining routes"),
        ]
    else:
        wave_text = [
            ("Wave 1 — First safe cuts (JSON and leaves)",
             "Read endpoints that return JSON, or read views with risk ≤ 5, with no database writes.",
             "Wave 1: independent read endpoints"),
            ("Wave 2 — Intermediate views and queries",
             "Read views with risk above 5 and up to 15, with no database writes.",
             "Wave 2: secondary views and catalogs"),
            ("Wave 3 — Transactional domain and critical writes",
             "POST routes, routes that write to the database, or routes with risk > 15.",
             "Wave 3: mutations and complex business rules"),
        ]
    waves: list[MigrationWave] = [
        MigrationWave(
            wave_number=index + 1,
            name=name,
            description=description,
            candidates=cands,
            pert=pert_for_candidates(cands, scope),
        )
        for index, ((name, description, scope), cands) in enumerate(zip(wave_text, (wave1_cands, wave2_cands, wave3_cands)))
    ]

    # PERT of the recommended cut
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
            scope_description=f"Recommended cut: {recommended.endpoint} ({recommended.function_name})",
        )

    # reference_comparison is filled only after a reference cut really runs (compare_with_reference).
    return MigrationRecommendation(
        recommended=recommended,
        alternatives=alternatives,
        do_not_start_here=do_not_start_here,
        candidates=candidates,
        waves=waves,
        first_cut_pert=first_cut_pert,
        reference_comparison=None,
    )


_PATH_PARAM = re.compile(r"<[^>]+>|\{[^}]+\}")


def _endpoint_shape(endpoint: str) -> str:
    """'GET /invoices/<int:invoice_id>' and 'GET /invoices/{id}' both become 'GET /invoices/{}'."""
    return _PATH_PARAM.sub("{}", " ".join(endpoint.split())).upper()


def compare_with_reference(
    recommendation: MigrationRecommendation,
    reference_endpoint: str | None,
    reference_status: str | None,
) -> MigrationRecommendation:
    """Explains how the engine's pick relates to the reference cut that was actually executed.

    Only a reference cut that ran (passed or failed) is compared; for uploads it never runs, so
    nothing is claimed about a laboratory cut that does not exist.
    """
    recommended = recommendation.recommended
    if recommended is None or not reference_endpoint or reference_status not in ("passed", "failed"):
        return recommendation.model_copy(update={"reference_comparison": None})
    reference_shape = _endpoint_shape(reference_endpoint)
    reference = next((c for c in recommendation.candidates if _endpoint_shape(c.endpoint) == reference_shape), None)
    verdict = "passed" if reference_status == "passed" else "did not pass"
    if reference is not None and reference.endpoint == recommended.endpoint:
        text = (
            f"The engine picked {recommended.endpoint} on its own, the same endpoint as the first reference cut "
            f"that was run; its characterization tests {verdict}."
        )
    elif reference is not None:
        text = (
            f"The engine recommends {recommended.endpoint} (score {recommended.score}), while the first reference "
            f"cut that was run is {reference.endpoint} (score {reference.score}); its tests {verdict}."
        )
    else:
        text = (
            f"The engine recommends {recommended.endpoint}; the first reference cut that was run "
            f"({reference_endpoint}) is not among the detected routes."
        )
    return recommendation.model_copy(update={"reference_comparison": text})
