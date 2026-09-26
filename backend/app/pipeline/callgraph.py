"""Grafo de llamadas real de un repositorio, construido con `ast` (solo análisis estático, nunca se ejecuta código).

Las funciones (incluidas anidadas y métodos) son nodos; una arista A -> B significa que A contiene una
llamada a un nombre que resuelve a B. Se resuelve por nombre dentro del mismo archivo o, si es único, en
todo el repo; los nombres ambiguos entre archivos se omiten para no inventar relaciones.
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

IGNORED_PARTS = {".git", ".venv", "venv", "__pycache__", "tests", "node_modules"}
ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "route"}


class FunctionCollector(ast.NodeVisitor):
    """Recolecta funciones (incluidas anidadas y métodos) y las llamadas que hace cada una."""

    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.stack: List[str] = []
        self.owners: List[str] = []
        self.functions: Dict[str, Dict[str, Any]] = {}

    def _enter(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualname = ".".join(self.stack + [node.name])
        route = route_of(node)
        dec_start = min((getattr(d, "lineno", node.lineno) for d in node.decorator_list), default=node.lineno)
        self.functions[qualname] = {
            "id": f"{self.rel_path}::{qualname}",
            "name": node.name,
            "qualname": qualname,
            "file": self.rel_path,
            "line_start": dec_start,
            "line_end": getattr(node, "end_lineno", node.lineno) or node.lineno,
            "route": route,
            "calls": set(),
        }
        self.stack.append(node.name)
        self.owners.append(qualname)
        self.generic_visit(node)
        self.owners.pop()
        self.stack.pop()

    visit_FunctionDef = _enter  # type: ignore[assignment]
    visit_AsyncFunctionDef = _enter  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if self.owners:
            target: Optional[str] = None
            if isinstance(node.func, ast.Name):
                target = node.func.id
            elif isinstance(node.func, ast.Attribute):
                target = node.func.attr
            if target:
                self.functions[self.owners[-1]]["calls"].add(target)
        self.generic_visit(node)


def route_of(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[Dict[str, Any]]:
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
            continue
        if dec.func.attr not in ROUTE_METHODS or not dec.args or not isinstance(dec.args[0], ast.Constant):
            continue
        methods = [dec.func.attr.upper()] if dec.func.attr != "route" else ["GET"]
        for kw in dec.keywords:
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                methods = [str(e.value).upper() for e in kw.value.elts if isinstance(e, ast.Constant)]
        return {"rule": str(dec.args[0].value), "methods": methods}
    return None


def normalize_rule(rule: str) -> str:
    return re.sub(r"(<[^>]+>|\{[^}]+\})", "{}", rule.strip())


def collect_functions(repo: Path) -> List[Dict[str, Any]]:
    functions: List[Dict[str, Any]] = []
    for py_file in sorted(repo.glob("**/*.py")):
        rel = py_file.relative_to(repo)
        if any(part in IGNORED_PARTS for part in rel.parts):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        collector = FunctionCollector(rel.as_posix())
        collector.visit(tree)
        functions.extend(collector.functions.values())
    return functions


def enclosing(functions: List[Dict[str, Any]], path: str, start: int, end: int) -> Optional[Dict[str, Any]]:
    """Función más pequeña del archivo que contiene el rango citado."""
    best: Optional[Dict[str, Any]] = None
    for fn in functions:
        if fn["file"] == path and fn["line_start"] <= start and end <= fn["line_end"]:
            if best is None or (fn["line_end"] - fn["line_start"]) < (best["line_end"] - best["line_start"]):
                best = fn
    return best


def resolve_edges(functions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Aristas caller -> callee entre funciones definidas en el repo."""
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for fn in functions:
        by_name.setdefault(fn["name"], []).append(fn)
    edges: List[Dict[str, str]] = []
    seen: set[Tuple[str, str]] = set()
    for fn in functions:
        for callee_name in sorted(fn["calls"]):
            candidates = by_name.get(callee_name, [])
            same_file = [c for c in candidates if c["file"] == fn["file"]]
            pool = same_file or (candidates if len(candidates) == 1 else [])
            for callee in pool:
                key = (fn["id"], callee["id"])
                if callee["id"] != fn["id"] and key not in seen:
                    seen.add(key)
                    edges.append({"source": fn["id"], "target": callee["id"]})
    return edges


def module_node(nodes: List[Dict[str, Any]], path: str, modern_files: set[str] | None = None) -> str:
    """Nodo de código a nivel de módulo, para evidencias fuera de cualquier función (p. ej. constantes)."""
    node_id = f"{path}::<module>"
    if not any(n["id"] == node_id for n in nodes):
        modern = modern_files or set()
        nodes.append({
            "id": node_id, "name": Path(path).name, "qualname": "<module>", "file": path,
            "line_start": 1, "line_end": 1, "route": None,
            "kind": "modern" if path.startswith("modern/") or path in modern else "legacy",
        })
    return node_id


def to_nodes(functions: List[Dict[str, Any]], modern_files: set[str] | None = None) -> List[Dict[str, Any]]:
    modern = modern_files or set()
    return [{
        "id": fn["id"], "name": fn["name"], "qualname": fn["qualname"], "file": fn["file"],
        "line_start": fn["line_start"], "line_end": fn["line_end"],
        "kind": "modern" if fn["file"].startswith("modern/") or fn["file"] in modern else "legacy",
        "route": fn["route"],
    } for fn in functions]
