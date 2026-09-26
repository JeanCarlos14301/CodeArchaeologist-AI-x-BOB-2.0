"""Extractor de Inventario de Código, Rutas Flask, Consultas SQL y Complejidad Radon (D-03).

Realiza análisis estático determinista sobre el árbol de código:
- Detección exhaustiva de rutas Flask (@app.route, @blueprint.route), métodos y controladores.
- Detección de consultas SQL con sqlglot y regex (análisis de concatenación insegura vs parametrización).
- Medición de complejidad ciclomática por función con radon (detección de monolitos).
- Análisis de dependencias e importaciones circulares (ej. billing <-> customers).
- Mapeo de esquema relacional a partir de DDL.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import radon.complexity as radon_cc
import sqlglot
from sqlglot import exp


@dataclass
class FlaskRouteInfo:
    file_path: str
    function_name: str
    rule: str
    http_methods: List[str]
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)


@dataclass
class SQLQueryInfo:
    file_path: str
    line_start: int
    line_end: int
    raw_snippet: str
    query_type: str  # SELECT, INSERT, UPDATE, DELETE, CREATE
    tables_referenced: List[str]
    is_concatenated_or_interpolated: bool
    is_parameterized: bool
    explanation: str


@dataclass
class FunctionComplexityInfo:
    file_path: str
    function_name: str
    line_start: int
    line_end: int
    complexity: int
    rank: str  # A, B, C, D, E, F
    is_monolithic: bool
    lines_count: int


@dataclass
class CodeInventoryReport:
    total_files: int
    routes: List[FlaskRouteInfo]
    sql_queries: List[SQLQueryInfo]
    complex_functions: List[FunctionComplexityInfo]
    circular_dependencies: List[List[str]]
    tables_detected: List[str]
    schema_ddl: Optional[str] = None


class FlaskRouteVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, source_lines: List[str]):
        self.rel_path = rel_path
        self.source_lines = source_lines
        self.routes: List[FlaskRouteInfo] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_route(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_route(node)
        self.generic_visit(node)

    def _check_route(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                func = dec.func
                attr_name = getattr(func, "attr", None) or getattr(func, "id", None)
                if attr_name in {"get", "post", "put", "delete", "patch", "route"}:
                    rule = "/"
                    if dec.args and isinstance(dec.args[0], ast.Constant):
                        rule = str(dec.args[0].value)

                    methods = [attr_name.upper()] if attr_name != "route" else ["GET"]
                    for kw in dec.keywords:
                        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                            methods = [
                                str(elt.value).upper()
                                for elt in kw.value.elts
                                if isinstance(elt, ast.Constant)
                            ]

                    end_line = getattr(node, "end_lineno", node.lineno)
                    doc = ast.get_docstring(node)
                    params = [a.arg for a in node.args.args]

                    self.routes.append(
                        FlaskRouteInfo(
                            file_path=self.rel_path,
                            function_name=node.name,
                            rule=rule,
                            http_methods=methods,
                            line_start=node.lineno,
                            line_end=end_line,
                            docstring=doc,
                            parameters=params,
                        )
                    )


class SQLCallVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, source_code: str):
        self.rel_path = rel_path
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.sql_queries: List[SQLQueryInfo] = []

    def visit_BinOp(self, node: ast.BinOp):
        # Detección de concatenación con '+' donde uno de los lados es una consulta SQL
        if isinstance(node.op, ast.Add):
            left_const = self._get_str_constant(node.left)
            right_const = self._get_str_constant(node.right)
            sql_text = left_const or right_const
            if sql_text and self._looks_like_sql(sql_text):
                end_line = getattr(node, "end_lineno", node.lineno)
                snippet = self._get_source_range(node.lineno, end_line)
                tables = self._extract_tables(sql_text)
                self.sql_queries.append(
                    SQLQueryInfo(
                        file_path=self.rel_path,
                        line_start=node.lineno,
                        line_end=end_line,
                        raw_snippet=snippet.strip(),
                        query_type=self._detect_sql_type(sql_text),
                        tables_referenced=tables,
                        is_concatenated_or_interpolated=True,
                        is_parameterized=False,
                        explanation="Consulta SQL armada mediante concatenación directa de cadenas (+), riesgo alto de SQL Injection.",
                    )
                )
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        # Detección de f-strings que contengan SQL
        fstring_source = self._get_source_range(node.lineno, getattr(node, "end_lineno", node.lineno))
        if self._looks_like_sql(fstring_source):
            tables = self._extract_tables(fstring_source)
            end_line = getattr(node, "end_lineno", node.lineno)
            self.sql_queries.append(
                SQLQueryInfo(
                    file_path=self.rel_path,
                    line_start=node.lineno,
                    line_end=end_line,
                    raw_snippet=fstring_source.strip(),
                    query_type=self._detect_sql_type(fstring_source),
                    tables_referenced=tables,
                    is_concatenated_or_interpolated=True,
                    is_parameterized=False,
                    explanation="Consulta SQL armada mediante interpolación en f-string, vulnerable a inyección SQL.",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detección de llamadas a execute, query_db, etc.
        fn_name = ""
        if isinstance(node.func, ast.Name):
            fn_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            fn_name = node.func.attr

        if fn_name in ["execute", "query_db", "executemany"]:
            if node.args:
                first_arg = node.args[0]
                sql_text = self._get_str_constant(first_arg)
                if sql_text and self._looks_like_sql(sql_text):
                    has_params = len(node.args) > 1 or any(kw.arg in ["args", "params"] for kw in node.keywords)
                    has_placeholders = "?" in sql_text or "%s" in sql_text
                    is_safe = has_params and has_placeholders
                    end_line = getattr(node, "end_lineno", node.lineno)
                    snippet = self._get_source_range(node.lineno, end_line)
                    tables = self._extract_tables(sql_text)

                    self.sql_queries.append(
                        SQLQueryInfo(
                            file_path=self.rel_path,
                            line_start=node.lineno,
                            line_end=end_line,
                            raw_snippet=snippet.strip(),
                            query_type=self._detect_sql_type(sql_text),
                            tables_referenced=tables,
                            is_concatenated_or_interpolated=not is_safe,
                            is_parameterized=is_safe,
                            explanation="Consulta parametrizada correctamente con placeholders." if is_safe else "Consulta ejecutada sin separación segura de parámetros.",
                        )
                    )
        self.generic_visit(node)

    def _get_str_constant(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _looks_like_sql(self, text: str) -> bool:
        t = text.strip().upper()
        return any(
            t.startswith(cmd) or f" {cmd} " in t
            for cmd in ["SELECT", "INSERT INTO", "UPDATE", "DELETE FROM", "CREATE TABLE", "WHERE"]
        )

    def _detect_sql_type(self, text: str) -> str:
        t = text.strip().upper()
        for cmd in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE"]:
            if cmd in t:
                return cmd
        return "QUERY"

    def _extract_tables(self, sql_text: str) -> List[str]:
        tables = []
        try:
            parsed = sqlglot.parse_one(sql_text, read="sqlite")
            for table_expr in parsed.find_all(exp.Table):
                tables.append(table_expr.name)
        except Exception:
            # Fallback regex
            matches = re.findall(
                r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z0-9_]+)",
                sql_text,
                re.IGNORECASE,
            )
            tables = [m.lower() for m in matches if m.lower() not in ["where", "set", "select", "values"]]
        return sorted(list(set(tables)))

    def _get_source_range(self, start: int, end: int) -> str:
        start_idx = max(0, start - 1)
        end_idx = min(len(self.source_lines), end)
        return "\n".join(self.source_lines[start_idx:end_idx])


def analyze_repository_inventory(repo_dir: Path | str) -> CodeInventoryReport:
    """Ejecuta el inventario completo sobre el repositorio indicado."""
    repo_path = Path(repo_dir)
    all_routes: List[FlaskRouteInfo] = []
    all_sql_queries: List[SQLQueryInfo] = []
    all_complexities: List[FunctionComplexityInfo] = []
    file_imports: Dict[str, Set[str]] = {}
    tables_detected: Set[str] = set()
    schema_ddl: Optional[str] = None
    python_files_count = 0

    # 1. Leer esquemas SQL si existen
    for sql_file in repo_path.glob("**/*.sql"):
        try:
            ddl_content = sql_file.read_text(encoding="utf-8")
            if not schema_ddl:
                schema_ddl = ddl_content
            for match in re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)", ddl_content, re.IGNORECASE):
                tables_detected.add(match.lower())
        except Exception:
            pass

    # 2. Analizar cada archivo Python
    for py_file in repo_path.glob("**/*.py"):
        if any(p in py_file.parts for p in [".git", ".venv", "venv", "__pycache__", "tests"]):
            continue
        python_files_count += 1
        rel_posix = py_file.relative_to(repo_path).as_posix()
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            lines = source.splitlines()

            # Rutas Flask
            route_visitor = FlaskRouteVisitor(rel_posix, lines)
            route_visitor.visit(tree)
            all_routes.extend(route_visitor.routes)

            # Consultas SQL
            sql_visitor = SQLCallVisitor(rel_posix, source)
            sql_visitor.visit(tree)
            all_sql_queries.extend(sql_visitor.sql_queries)
            for q in sql_visitor.sql_queries:
                for t in q.tables_referenced:
                    tables_detected.add(t.lower())

            # Complejidad ciclomática Radon (incluyendo closures/rutas dentro de application factory)
            def _extract_all_radon_blocks(blocks_list):
                results = []
                for blk in blocks_list:
                    if hasattr(blk, "complexity") and hasattr(blk, "name"):
                        results.append(blk)
                    for sub in getattr(blk, "closures", []):
                        results.extend(_extract_all_radon_blocks([sub]))
                    for sub in getattr(blk, "methods", []):
                        results.extend(_extract_all_radon_blocks([sub]))
                return results

            blocks = radon_cc.cc_visit(source)
            for b in _extract_all_radon_blocks(blocks):
                lines_count = getattr(b, "endline", b.lineno) - b.lineno + 1
                is_mono = (b.complexity >= 10) or (lines_count >= 50)
                all_complexities.append(
                    FunctionComplexityInfo(
                        file_path=rel_posix,
                        function_name=b.name,
                        line_start=b.lineno,
                        line_end=getattr(b, "endline", b.lineno),
                        complexity=b.complexity,
                        rank=radon_cc.cc_rank(b.complexity),
                        is_monolithic=is_mono,
                        lines_count=lines_count,
                    )
                )

            # Importaciones
            imports_in_file = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports_in_file.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports_in_file.add(node.module)
            file_imports[rel_posix] = imports_in_file

        except Exception:
            continue

    # 3. Detectar dependencias circulares
    circular_deps: List[List[str]] = []
    modules = list(file_imports.keys())
    for i in range(len(modules)):
        m1 = modules[i]
        stem1 = Path(m1).stem
        for j in range(i + 1, len(modules)):
            m2 = modules[j]
            stem2 = Path(m2).stem
            m1_imports_m2 = any(stem2 == imp or imp.startswith(f"{stem2}.") for imp in file_imports[m1])
            m2_imports_m1 = any(stem1 == imp or imp.startswith(f"{stem1}.") for imp in file_imports[m2])
            if m1_imports_m2 and m2_imports_m1:
                circular_deps.append([m1, m2, m1])

    return CodeInventoryReport(
        total_files=python_files_count,
        routes=all_routes,
        sql_queries=all_sql_queries,
        complex_functions=sorted(all_complexities, key=lambda x: x.complexity, reverse=True),
        circular_dependencies=circular_deps,
        tables_detected=sorted(list(tables_detected)),
        schema_ddl=schema_ddl,
    )
