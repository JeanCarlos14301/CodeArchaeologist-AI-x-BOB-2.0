"""Auditoría real de repositorios subidos y vistas derivadas del análisis estático.

Nada de esto usa datos de ejemplo:
- POST /api/audits/upload : ZIP -> extracción segura -> Bob real (evidence-auditor) -> validación de evidencia.
  Exige SIEMPRE el token `X-Live-Token` (variable LIVE_AUDIT_TOKEN); sin la variable, el servidor rechaza cargas.
- GET  /api/audits/{id}/graph        : funciones y llamadas reales (AST) con las marcas del expediente.
- GET  /api/audits/{id}/architecture : módulos, dependencias, rutas y complejidad medidos sobre el código.
- GET  /api/audits/{id}/files/{name} : descarga del expediente y de la respuesta cruda de Bob.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.access import require_job_access, require_upload_token
from app.contracts.schema_v1 import Dossier
from app.extractors.code_inventory import analyze_repository_inventory
from app.jobs.service import AuditService, BusyError, NotFoundError
from app.jobs.store import Job
from app.pipeline.callgraph import collect_functions, enclosing, module_node, resolve_edges, to_nodes
from app.pipeline.evidence_audit import BOB_RESULT_FILE, DOSSIER_FILE
from app.pipeline.migration_ranking import analyze_route_candidates
from app.renderers.board_memo import BOARD_MEMO_FILE
from app.sandbox.reference_cut import MIGRATION_DIFF_FILE, SANDBOX_DIR
from app.validators.evidence import resolve_inside
from app.pipeline.ingestion import MAX_ZIP_COMPRESSED_BYTES

router = APIRouter(prefix="/api/audits", tags=["live"])

DOWNLOADABLE = {
    DOSSIER_FILE: "application/json",
    BOB_RESULT_FILE: "application/json",
    BOARD_MEMO_FILE: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    MIGRATION_DIFF_FILE: "text/x-diff",
}
SEVERITY_RANK = ["critical", "high", "medium", "low"]
_SAFE_LABEL = re.compile(r"[^A-Za-z0-9_./ -]")


def get_service(request: Request) -> AuditService:
    return request.app.state.audit_service


Service = Annotated[AuditService, Depends(get_service)]


def _safe_name(filename: str | None) -> str:
    name = Path((filename or "repositorio.zip").replace("\\", "/")).name
    return _SAFE_LABEL.sub("_", name)[:80] or "repositorio.zip"


@router.post("/upload", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def upload_audit(
    service: Service,
    zip_file: Annotated[UploadFile, File()],
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
    purpose: Annotated[Literal["audit", "modernization"], Form()] = "audit",
) -> Job:
    require_upload_token(x_live_token)
    data = await zip_file.read(MAX_ZIP_COMPRESSED_BYTES + 1)
    if len(data) > MAX_ZIP_COMPRESSED_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"El ZIP supera {MAX_ZIP_COMPRESSED_BYTES // (1024 * 1024)} MB.")
    if not data.startswith(b"PK"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no es un ZIP válido.")
    try:
        return service.start_upload(_safe_name(zip_file.filename), data, purpose)
    except BusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


def _workspace(service: AuditService, job_id: str, token: str | None) -> Path:
    try:
        job = service.get_job(job_id)
        require_job_access(job, token)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    workspace = service.job_dir(job_id) / "workspace"
    if not workspace.is_dir():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El código de este análisis aún no está disponible.")
    return workspace


def _dossier(service: AuditService, job_id: str) -> Dossier | None:
    try:
        return service.get_dossier(job_id)
    except NotFoundError:
        return None


@router.get("/{job_id}/graph")
def read_graph(
    job_id: str,
    service: Service,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> dict[str, Any]:
    workspace = _workspace(service, job_id, x_live_token)
    dossier = _dossier(service, job_id)
    functions = collect_functions(workspace)
    nodes = to_nodes(functions)
    edges = resolve_edges(functions)

    callers: dict[str, set[str]] = {}
    for edge in edges:
        callers.setdefault(edge["target"], set()).add(edge["source"])

    marks: list[dict[str, Any]] = []
    blast: list[dict[str, Any]] = []
    if dossier:
        for status_name, findings in (("accepted", dossier.findings), ("rejected", dossier.rejected_findings)):
            for finding in findings:
                origins: set[str] = set()
                for ev in finding.evidence:
                    fn = enclosing(functions, ev.path, ev.line_start, ev.line_end)
                    node_id = fn["id"] if fn else module_node(nodes, ev.path)
                    origins.add(node_id)
                    marks.append({
                        "finding_id": finding.id, "title": finding.title, "severity": finding.severity, "status": status_name,
                        "node": node_id, "path": ev.path, "line_start": ev.line_start, "line_end": ev.line_end,
                    })
                if status_name == "accepted":
                    # Radio de explosión: quién llama, directa o indirectamente, a la función afectada.
                    impacted: set[str] = set()
                    frontier = list(origins)
                    while frontier:
                        for caller in callers.get(frontier.pop(), ()):
                            if caller not in impacted and caller not in origins:
                                impacted.add(caller)
                                frontier.append(caller)
                    blast.append({
                        "finding_id": finding.id, "severity": finding.severity, "score": None,
                        "origin_nodes": sorted(origins), "impacted_nodes": sorted(impacted), "unresolved_symbols": [],
                    })

    return {
        "job_id": job_id,
        "job_status": service.get_job(job_id).status,
        "has_result": dossier is not None,
        "nodes": nodes,
        "edges": edges,
        "findings": marks,
        "blast_radius": blast,
        "migration_cut": None,
        "notes": "Grafo medido con AST sobre el código subido. Aristas resueltas por nombre de función; los nombres ambiguos entre archivos se omiten. Impacto = llamadores directos e indirectos de la función con la evidencia.",
    }


def _label(text: str) -> str:
    return _SAFE_LABEL.sub("_", text)


def _mermaid(modules: list[dict[str, Any]], deps: list[dict[str, Any]]) -> str:
    ids = {m["file"]: f"m{i}" for i, m in enumerate(modules)}
    lines = ["flowchart LR"]
    for m in modules:
        suffix = f"<br/>{m['functions']} funciones" + (f" · {m['findings']} hallazgos" if m["findings"] else "")
        lines.append(f'  {ids[m["file"]]}["{_label(m["file"])}{suffix}"]:::{m["worst_severity"] or "clean"}')
    for d in deps:
        lines.append(f'  {ids[d["source"]]} -->|"{d["calls"]}"| {ids[d["target"]]}')
    lines += [
        "  classDef clean fill:#0e3a4f,stroke:#38bdf8,color:#e6edf3,stroke-width:2px;",
        "  classDef critical fill:#4a1420,stroke:#fb7185,color:#e6edf3,stroke-width:3px;",
        "  classDef high fill:#4a2a10,stroke:#fb923c,color:#e6edf3,stroke-width:3px;",
        "  classDef medium fill:#453a10,stroke:#fbbf24,color:#e6edf3,stroke-width:2px;",
        "  classDef low fill:#2a3340,stroke:#94a3b8,color:#e6edf3,stroke-width:2px;",
    ]
    return "\n".join(lines)


@router.get("/{job_id}/architecture")
def read_architecture(
    job_id: str,
    service: Service,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> dict[str, Any]:
    workspace = _workspace(service, job_id, x_live_token)
    dossier = _dossier(service, job_id)
    functions = collect_functions(workspace)
    edges = resolve_edges(functions)
    file_of = {fn["id"]: fn["file"] for fn in functions}

    worst: dict[str, str] = {}
    per_file: Counter[str] = Counter()
    for finding in dossier.findings if dossier else []:
        for file in {ev.path for ev in finding.evidence}:
            per_file[file] += 1
            if file not in worst or SEVERITY_RANK.index(finding.severity) < SEVERITY_RANK.index(worst[file]):
                worst[file] = finding.severity

    files = sorted({fn["file"] for fn in functions} | set(per_file))
    modules = [{
        "file": file,
        "functions": sum(1 for fn in functions if fn["file"] == file),
        "findings": per_file.get(file, 0),
        "worst_severity": worst.get(file),
    } for file in files]

    cross: Counter[tuple[str, str]] = Counter()
    for edge in edges:
        a, b = file_of[edge["source"]], file_of[edge["target"]]
        if a != b:
            cross[(a, b)] += 1
    deps = [{"source": a, "target": b, "calls": n} for (a, b), n in sorted(cross.items())]

    inventory = analyze_repository_inventory(workspace)
    return {
        "job_id": job_id,
        "modules": modules,
        "dependencies": deps,
        "mermaid": _mermaid(modules, deps) if modules else None,
        "routes": [
            {"methods": r.http_methods, "rule": r.rule, "file": r.file_path, "function": r.function_name, "line_start": r.line_start}
            for r in inventory.routes
        ] + [
            {"methods": fn["route"]["methods"], "rule": fn["route"]["rule"], "file": fn["file"], "function": fn["name"], "line_start": fn["line_start"]}
            for fn in functions if fn["route"] and not any(r.file_path == fn["file"] and r.function_name == fn["name"] for r in inventory.routes)
        ],
        "complex_functions": [
            {"file": c.file_path, "name": c.function_name, "line_start": c.line_start, "complexity": c.complexity, "rank": c.rank, "lines": c.lines_count}
            for c in inventory.complex_functions[:10]
        ],
        "circular_dependencies": inventory.circular_dependencies,
        "tables": inventory.tables_detected,
        "sql": {
            "total": len(inventory.sql_queries),
            "concatenated": sum(1 for q in inventory.sql_queries if q.is_concatenated_or_interpolated),
            "parameterized": sum(1 for q in inventory.sql_queries if q.is_parameterized),
        },
        "totals": {"files": inventory.total_files, "functions": len(functions), "calls": len(edges)},
    }


@router.get("/{job_id}/migration")
def read_migration(
    job_id: str,
    service: Service,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> dict[str, Any]:
    try:
        job = service.get_job(job_id)
        require_job_access(job, x_live_token)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        dossier = service.get_dossier(job_id)
    except NotFoundError:
        dossier = None

    if dossier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El resultado de migración aún no está disponible.")

    workspace = service.job_dir(job_id) / "workspace"
    recommendation = dossier.recommendation
    if recommendation is None and workspace.is_dir():
        recommendation = analyze_route_candidates(workspace, dossier)

    sandbox = service.job_dir(job_id) / SANDBOX_DIR

    def content(relative: str | None) -> str | None:
        if relative is None:
            return None
        target = resolve_inside(sandbox.resolve(), relative)
        return target.read_text(encoding="utf-8", errors="replace") if target and target.is_file() else None

    migration_result = (
        dossier.migration.model_dump()
        if dossier.migration
        else {
            "status": "not_run",
            "reason": "Primer corte de caracterización no ejecutado para este repositorio.",
            "implementation_origin": "strangler-fig",
            "endpoint": recommendation.recommended.endpoint if recommendation and recommendation.recommended else "None",
            "tests": [],
            "legacy_file": None,
            "modern_file": None,
            "facade_file": None,
            "diff_file": None,
        }
    )

    rec_dump = recommendation.model_dump() if recommendation else None
    first_pert = (
        recommendation.first_cut_pert.model_dump()
        if recommendation and recommendation.first_cut_pert
        else (dossier.first_cut_pert.model_dump() if dossier.first_cut_pert else None)
    )

    return {
        "job_id": job_id,
        "result": migration_result,
        "recommendation": rec_dump,
        "candidates": rec_dump["candidates"] if rec_dump else [],
        "recommended": rec_dump["recommended"] if rec_dump else None,
        "alternatives": rec_dump["alternatives"] if rec_dump else [],
        "do_not_start_here": rec_dump["do_not_start_here"] if rec_dump else None,
        "waves": rec_dump["waves"] if rec_dump else [],
        "first_cut_pert": first_pert,
        "reference_comparison": rec_dump.get("reference_comparison") if rec_dump else None,
        "legacy_code": content(dossier.migration.legacy_file) if dossier.migration else None,
        "modern_code": content(dossier.migration.modern_file) if dossier.migration else None,
        "facade_code": content(dossier.migration.facade_file) if dossier.migration else None,
    }


@router.get("/{job_id}/files/{name}")
def download_file(
    job_id: str,
    name: str,
    service: Service,
    x_live_token: Annotated[str | None, Header(max_length=200)] = None,
) -> FileResponse:
    if name not in DOWNLOADABLE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no disponible.")
    try:
        job = service.get_job(job_id)
        require_job_access(job, x_live_token)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    path = service.job_dir(job_id) / name
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no disponible.")
    return FileResponse(path, media_type=DOWNLOADABLE[name], filename=f"{job_id}-{name}")
