"""Router para la Descarga Segura de Artefactos Generados (D-05, D-08, D-09).

Endpoint:
- GET /api/jobs/{id}/artifacts/{kind} : Descarga docx, html, pptx o diff.
Protección: no permite rutas arbitrarias, solo los 4 tipos autorizados.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.database import get_job, get_job_result
from backend.app.models import DossierResult
from backend.app.renderers.docx_renderer import render_dossier_to_docx
from backend.app.renderers.html_renderer import render_dossier_to_html
from backend.app.renderers.pptx_renderer import create_executive_pptx

router = APIRouter(prefix="/api/jobs", tags=["artifacts"])
BASE_DIR = Path(__file__).resolve().parent.parent.parent


KIND_CONFIG = {
    "docx": {
        "filename": "board_memo.docx",
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "renderer": render_dossier_to_docx,
    },
    "html": {
        "filename": "report.html",
        "media_type": "text/html; charset=utf-8",
        "renderer": render_dossier_to_html,
    },
    "pptx": {
        "filename": "presentation.pptx",
        "media_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "renderer": create_executive_pptx,
    },
    "diff": {
        "filename": "migration.diff",
        "media_type": "text/plain; charset=utf-8",
        "renderer": None,
    },
    "patch": {
        "filename": "migration.diff",
        "media_type": "text/plain; charset=utf-8",
        "renderer": None,
    },
}


@router.get("/{job_id}/artifacts/{kind}")
def download_artifact(job_id: str, kind: str) -> FileResponse:
    """Descarga de forma segura un artefacto del job."""
    kind_lower = kind.lower()
    if kind_lower not in KIND_CONFIG:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de artefacto no soportado: '{kind}'. Use 'docx', 'html', 'pptx' o 'diff'.",
        )

    config = KIND_CONFIG[kind_lower]
    target_filename = config["filename"]
    artifact_path = BASE_DIR / "artifacts" / job_id / target_filename

    # Si el archivo ya existe en disco, servirlo directamente
    if artifact_path.exists():
        return FileResponse(
            path=str(artifact_path),
            filename=f"{job_id[:8]}_{target_filename}",
            media_type=config["media_type"],
        )

    # Si no existe en disco pero el job está completado, regenerar al vuelo
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"El job aún no ha completado la generación de artefactos (estado actual: {job['status']}).",
        )

    result_json = get_job_result(job_id)
    if not result_json:
        raise HTTPException(status_code=404, detail="Expediente no encontrado para generar el artefacto.")

    dossier = DossierResult.model_validate(result_json)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    if config["renderer"]:
        config["renderer"](dossier, artifact_path)
    elif kind_lower in ["diff", "patch"]:
        patch_text = dossier.migration_summary.diff_patch if dossier.migration_summary else "No diff available."
        artifact_path.write_text(patch_text, encoding="utf-8")

    if not artifact_path.exists():
        raise HTTPException(status_code=500, detail="Error al generar el artefacto solicitado.")

    return FileResponse(
        path=str(artifact_path),
        filename=f"{job_id[:8]}_{target_filename}",
        media_type=config["media_type"],
    )
