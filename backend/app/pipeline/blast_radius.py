"""Deterministic blast radius module (shift-left, before the PR; not wired into the product).

Computes the transitive impact of source code changes on the rest of the system
through directed graphs (NetworkX) and AST inspection.
Follows the AGENTS.md rule: 'Numbers are computed by code, not by the AI'.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import networkx as nx  # type: ignore

try:
    from pydantic import BaseModel, Field  # type: ignore
except ImportError:
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self) -> Dict[str, Any]:
            return self.__dict__
        def model_dump_json(self, indent: int = 2) -> str:
            import json
            return json.dumps(self.__dict__, indent=indent)
    def Field(*args, **kwargs):  # type: ignore
        return None


class BlastRadiusReport(BaseModel):
    total_functions_count: int
    modified_symbols: List[str]
    direct_callers: List[str]
    transitive_impacted_symbols: List[str]
    direct_impact_ratio: float
    transitive_blast_radius_percent: float
    database_mutation_vulnerability: float
    composite_blast_radius_score: float
    verdict: str  # GREEN_PASS, YELLOW_REVIEW, RED_BLOCK
    recommendations: List[str]
    execution_mode: str = "live"


class CallGraphBuilder(ast.NodeVisitor):
    """Builds an intra-repository call graph using the Python AST."""

    def __init__(self, current_module: str, graph: nx.DiGraph):
        self.current_module = current_module
        self.graph = graph
        self.current_func: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self.current_func
        func_id = f"{self.current_module}.{node.name}"
        self.current_func = func_id
        self.graph.add_node(func_id, file=self.current_module, line=node.lineno)

        self.generic_visit(node)
        self.current_func = prev_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev_func = self.current_func
        func_id = f"{self.current_module}.{node.name}"
        self.current_func = func_id
        self.graph.add_node(func_id, file=self.current_module, line=node.lineno)

        self.generic_visit(node)
        self.current_func = prev_func

    def visit_Call(self, node: ast.Call):
        if self.current_func:
            target_name = None
            if isinstance(node.func, ast.Name):
                target_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                target_name = node.func.attr

            if target_name:
                # Arista dirigida: Caller -> Callee
                self.graph.add_edge(self.current_func, target_name)

        self.generic_visit(node)


def build_repository_call_graph(repo_dir: str | Path) -> nx.DiGraph:
    """Scans every .py file in the repository and builds the directed call graph."""
    graph = nx.DiGraph()
    repo_path = Path(repo_dir)

    for py_file in repo_path.glob("**/*.py"):
        if any(ignored in py_file.parts for ignored in [".git", ".venv", "venv", "__pycache__", "tests"]):
            continue
        try:
            rel_module = py_file.relative_to(repo_path).as_posix()
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            visitor = CallGraphBuilder(rel_module, graph)
            visitor.visit(tree)
        except Exception:
            continue

    return graph


def simulate_blast_radius(
    repo_dir: str | Path,
    modified_symbols: List[str],
    database_touched: bool = False,
    schema_dropped_or_altered: bool = False,
    test_coverage_ratio: float = 0.5,
) -> BlastRadiusReport:
    """Computes the deterministic Composite Blast Radius Score (CBRS) for a list of modified symbols."""
    graph = build_repository_call_graph(repo_dir)
    total_funcs = max(graph.number_of_nodes(), 1)

    # Invert the graph to follow who calls whom (Callee -> Callers)
    rev_graph = graph.reverse(copy=True)

    direct_callers: Set[str] = set()
    transitive_impacted: Set[str] = set()

    for sym in modified_symbols:
        # Find nodes that match the symbol
        matching_nodes = [n for n in graph.nodes if sym in n or n.endswith(f".{sym}")]
        for node in matching_nodes:
            # Direct callers
            direct = set(rev_graph.successors(node))
            direct_callers.update(direct)
            # Transitive callers (the whole cascade upward)
            if nx.has_path(rev_graph, node, node):
                pass
            transitive = nx.descendants(rev_graph, node)
            transitive_impacted.update(transitive)

    direct_count = len(direct_callers)
    transitive_count = len(transitive_impacted)

    direct_ratio = round(direct_count / total_funcs, 4)
    transitive_pct = round((transitive_count / total_funcs) * 100.0, 2)

    # Database Mutation Vulnerability (DMV)
    if schema_dropped_or_altered:
        dmv = 1.0
    elif database_touched:
        dmv = 0.5
    else:
        dmv = 0.0

    # Test Deficit Factor (1.0 = cero tests, 0.0 = 100% tests)
    test_deficit = max(0.0, min(1.0, 1.0 - test_coverage_ratio))

    # Composite Blast Radius Score (0 a 100)
    # CBRS = 0.4*TBR + 0.3*(DMV*100) + 0.3*(TestDeficit*100)
    cbrs = round((0.4 * min(transitive_pct, 100.0)) + (0.3 * (dmv * 100.0)) + (0.3 * (test_deficit * 100.0)), 2)

    recommendations = []
    if cbrs >= 60.0:
        verdict = "RED_BLOCK"
        recommendations.append("Automatic PR block: critical systemic impact detected.")
        recommendations.append("Convene the adversarial tribunal (/code-tribunal) before continuing.")
        recommendations.append("Write golden-master characterization tests with contract-keeper.")
    elif cbrs >= 25.0:
        verdict = "YELLOW_REVIEW"
        recommendations.append("Technical review required: moderate blast radius.")
        recommendations.append("Check test coverage in the affected calling modules.")
    else:
        verdict = "GREEN_PASS"
        recommendations.append("Low risk: fit for a regular review.")

    return BlastRadiusReport(
        total_functions_count=total_funcs,
        modified_symbols=modified_symbols,
        direct_callers=sorted(list(direct_callers)),
        transitive_impacted_symbols=sorted(list(transitive_impacted)),
        direct_impact_ratio=direct_ratio,
        transitive_blast_radius_percent=transitive_pct,
        database_mutation_vulnerability=dmv,
        composite_blast_radius_score=cbrs,
        verdict=verdict,
        recommendations=recommendations,
    )
