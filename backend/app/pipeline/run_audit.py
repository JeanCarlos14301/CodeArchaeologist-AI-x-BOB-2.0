"""CLI de las etapas 2 y 3.

Uso (desde backend/):
    python -m app.pipeline.run_audit ../samples/facturaya-v1
    python -m app.pipeline.run_audit <repo> --import ../artifacts/jobs/<id>/bob-result.json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from app.pipeline.evidence_audit import AuditError, run_evidence_audit

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "jobs"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoría de evidencia con IBM Bob (etapas 2 y 3).")
    parser.add_argument("repo", type=Path, help="Ruta al repositorio legado a auditar.")
    parser.add_argument("--import", dest="imported", type=Path, help="bob-result.json exportado (modo asistido).")
    parser.add_argument("--job-dir", type=Path, help="Directorio de salida (por defecto artifacts/jobs/<timestamp>).")
    args = parser.parse_args(argv)

    job_dir = args.job_dir or ARTIFACTS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        dossier = run_evidence_audit(args.repo.resolve(), job_dir.resolve(), imported_result=args.imported)
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    stats = dossier.stats
    print(f"execution_mode: {dossier.execution_mode}")
    print(f"Hallazgos reportados: {stats.findings_reported} · validados: {stats.findings_validated}")
    print(f"Evidencias válidas: {stats.evidence_valid}/{stats.evidence_total} ({stats.evidence_valid_ratio:.0%})")
    if stats.bob_cost is not None:
        print(f"Coste Bob: {stats.bob_cost} · duración: {stats.bob_duration_ms} ms")
    for finding in dossier.findings:
        first = finding.evidence[0]
        print(f"  [{finding.severity:>8}] {finding.id} {finding.title} — {first.path}:{first.line_start}")
    for finding in dossier.rejected_findings:
        print(f"  [RECHAZADO] {finding.id} {finding.title}")
    print(f"Expediente: {job_dir / 'dossier.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
