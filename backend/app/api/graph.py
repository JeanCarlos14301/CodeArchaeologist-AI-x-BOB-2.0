"""Grafo de llamadas real de un job y lector de fuentes del sandbox (visualización del frontend).

Endpoints:
- GET /api/jobs/{id}/graph  : funciones del repo del job (AST real), llamadas entre ellas y las
  marcas que el pipeline dejó sobre cada función (hallazgos, radio de explosión, corte de migración).
- GET /api/jobs/{id}/source : fragmento de un archivo del sandbox con numeración de líneas.

Nada se inventa: los nodos y aristas salen de `ast` sobre `sandboxes/{id}/repo`; las marcas salen del
DossierResult guardado en SQLite. Las aristas se resuelven por nombre de función y se descartan si
el nombre es ambiguo entre archivos.
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from backend.app.database import get_job, get_job_result

router = APIRouter(prefix="/api/jobs", tags=["graph"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
JOB_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")
IGNORED_PARTS = {".git", ".venv", "venv", "__pycache__", "tests", "node_modules"}
SOURCE_SUFFIXES = {".py", ".sql", ".md", ".txt", ".diff", ".yaml", ".yml", ".json"}
MAX_SOURCE_LINES = 400
MAX_SOURCE_BYTES = 1_000_000
ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "route"}


def _job_repo(job_id: str) -> Tuple[Dict[str, Any], Path]:
    if not JOB_ID_RE.match(job_id):
        raise HTTPException(status_code=404, detail="Job no encontrado")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")
    repo = BASE_DIR / "sandboxes" / job_id / "repo"
    if not repo.is_dir():
        raise HTTPException(status_code=404, detail="El sandbox de este job aún no está disponible")
    return job, repo


class _FunctionCollector(ast.NodeVisitor):
    """Recolecta funciones (incluidas anidadas y métodos) y las llamadas que hace cada una."""

    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.stack: List[str] = []
        self.owners: List[str] = []
        self.functions: Dict[str, Dict[str, Any]] = {}

    def _enter(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualname = ".".join(self.stack + [node.name])
        route = _route_of(node)
        self.functions[qualname] = {
            "id": f"{self.rel_path}::{qualname}",
            "name": node.name,
            "qualname": qualname,
            "file": self.rel_path,
            "line_start": node.lineno,
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


def _route_of(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[Dict[str, Any]]:
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


def _normalize_rule(rule: str) -> str:
    return re.sub(r"(<[^>]+>|\{[^}]+\})", "{}", rule.strip())


def _collect(repo: Path) -> List[Dict[str, Any]]:
    functions: List[Dict[str, Any]] = []
    for py_file in sorted(repo.glob("**/*.py")):
        rel = py_file.relative_to(repo)
        if any(part in IGNORED_PARTS for part in rel.parts):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        collector = _FunctionCollector(rel.as_posix())
        collector.visit(tree)
        functions.extend(collector.functions.values())
    return functions


def _enclosing(functions: List[Dict[str, Any]], path: str, start: int, end: int) -> Optional[Dict[str, Any]]:
    """Función más pequeña del archivo que contiene el rango citado."""
    best: Optional[Dict[str, Any]] = None
    for fn in functions:
        if fn["file"] == path and fn["line_start"] <= start and end <= fn["line_end"]:
            if best is None or (fn["line_end"] - fn["line_start"]) < (best["line_end"] - best["line_start"]):
                best = fn
    return best


def _resolve_symbol(functions: List[Dict[str, Any]], symbol: str) -> Optional[Dict[str, Any]]:
    """Resuelve 'modulo.funcion' del radio de explosión contra los nodos reales."""
    module, _, name = symbol.rpartition(".")
    stem = module.split(".")[-1]
    matches = [f for f in functions if f["name"] == name and Path(f["file"]).stem == stem]
    return matches[0] if len(matches) == 1 else None


def _module_node(nodes: List[Dict[str, Any]], path: str, modern_files: set[str]) -> str:
    """Nodo de código a nivel de módulo, para evidencias fuera de cualquier función (p. ej. constantes)."""
    node_id = f"{path}::<module>"
    if not any(n["id"] == node_id for n in nodes):
        nodes.append({
            "id": node_id, "name": Path(path).name, "qualname": "<module>", "file": path,
            "line_start": 1, "line_end": 1, "route": None,
            "kind": "modern" if path.startswith("modern/") or path in modern_files else "legacy",
        })
    return node_id


@router.get("/{job_id}/graph")
def get_job_graph(job_id: str) -> Dict[str, Any]:
    """Grafo de funciones del job con las marcas que dejó cada etapa del pipeline."""
    job, repo = _job_repo(job_id)
    result = get_job_result(job_id) or {}
    migration = result.get("migration_summary") or {}
    modern_files = set(migration.get("modern_code_files") or [])
    if migration.get("facade_router_file"):
        modern_files.add(migration["facade_router_file"])

    functions = _collect(repo)
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for fn in functions:
        by_name.setdefault(fn["name"], []).append(fn)

    nodes: List[Dict[str, Any]] = []
    for fn in functions:
        is_modern = fn["file"].startswith("modern/") or fn["file"] in modern_files
        nodes.append({
            "id": fn["id"], "name": fn["name"], "qualname": fn["qualname"], "file": fn["file"],
            "line_start": fn["line_start"], "line_end": fn["line_end"],
            "kind": "modern" if is_modern else "legacy",
            "route": fn["route"],
        })

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

    # Marcas de hallazgos: función que contiene cada evidencia citada.
    finding_marks: List[Dict[str, Any]] = []
    blast: List[Dict[str, Any]] = []
    for finding in result.get("findings") or []:
        hit_nodes: List[str] = []
        for ev in finding.get("evidence") or []:
            fn = _enclosing(functions, ev["path"], ev["line_start"], ev["line_end"])
            node_id = fn["id"] if fn else _module_node(nodes, ev["path"], modern_files)
            finding_marks.append({
                "finding_id": finding["id"], "title": finding["title"], "severity": finding["severity"],
                "status": finding.get("status", "accepted"),
                "node": node_id, "path": ev["path"],
                "line_start": ev["line_start"], "line_end": ev["line_end"],
            })
            hit_nodes.append(node_id)
        resolved, unresolved = [], []
        for symbol in finding.get("transitive_impacted_symbols") or []:
            fn = _resolve_symbol(functions, symbol)
            (resolved if fn else unresolved).append(fn["id"] if fn else symbol)
        blast.append({
            "finding_id": finding["id"], "severity": finding["severity"],
            "score": finding.get("blast_radius_score", 0.0),
            "origin_nodes": sorted(set(hit_nodes)), "impacted_nodes": resolved, "unresolved_symbols": unresolved,
        })

    # Corte de migración: la ruta legada equivalente y lo que la reemplaza.
    cut: Optional[Dict[str, Any]] = None
    endpoint = result.get("selected_first_cut")
    if endpoint and migration:
        method, _, rule = endpoint.partition(" ")
        target = _normalize_rule(rule)
        legacy = [
            f for f in functions
            if f["route"] and method.upper() in f["route"]["methods"] and _normalize_rule(f["route"]["rule"]) == target
            and not f["file"].startswith("modern/")
        ]
        patch = migration.get("diff_patch", "")
        cut = {
            "endpoint": endpoint,
            "legacy_node": legacy[0]["id"] if legacy else None,
            "modern_nodes": [n["id"] for n in nodes if n["kind"] == "modern"],
            "modern_files": sorted(modern_files),
            "diff_added": sum(1 for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")),
            "diff_removed": sum(1 for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")),
            "legacy_tests_verdict": migration.get("legacy_tests_verdict"),
            "modern_tests_verdict": migration.get("modern_tests_verdict"),
        }

    return {
        "job_id": job_id,
        "job_status": job["status"],
        "has_result": bool(result),
        "nodes": nodes,
        "edges": edges,
        "findings": finding_marks,
        "blast_radius": blast,
        "migration_cut": cut,
        "notes": "Aristas resueltas por nombre de función dentro del repo; los nombres ambiguos entre archivos se omiten.",
    }


@router.get("/{job_id}/source")
def read_job_source(
    job_id: str,
    path: str = Query(..., min_length=1, max_length=300),
    start: int = Query(1, ge=1),
    end: int = Query(MAX_SOURCE_LINES, ge=1),
) -> Dict[str, Any]:
    """Devuelve líneas de un archivo del sandbox del job (solo lectura, sin salir del repo)."""
    _, repo = _job_repo(job_id)
    target = (repo / path).resolve()
    try:
        target.relative_to(repo.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    if not target.is_file() or target.suffix not in SOURCE_SUFFIXES or target.stat().st_size > MAX_SOURCE_BYTES:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    text = target.read_text(encoding="utf-8", errors="replace").splitlines()
    end = min(end, start + MAX_SOURCE_LINES - 1, len(text))
    return {
        "path": target.relative_to(repo.resolve()).as_posix(),
        "start": start,
        "end": end,
        "total_lines": len(text),
        "lines": [{"number": i, "text": text[i - 1]} for i in range(start, end + 1)],
    }
