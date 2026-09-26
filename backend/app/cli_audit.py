"""CLI de Auditoría y Diagnóstico Forense (CodeArchaeologist CLI).

Permite ejecutar el pipeline determinista y la auditoría forense directamente
desde la terminal sin necesidad de levantar el servidor web:
    python -m backend.app.cli_audit --sample samples/facturaya-v1/
"""

import argparse
import sys
import time
import uuid
from pathlib import Path

from backend.app.adapters.bob_adapter import REPO_ROOT, determine_operational_mode
from backend.app.pipeline.evidence_audit import (
    BOARD_MEMO_FILE,
    DOSSIER_FILE,
    run_evidence_audit,
)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="CodeArchaeologist CLI — Auditoría y modernización forense")
    parser.add_argument(
        "--sample",
        type=str,
        default="samples/facturaya-v1",
        help="Ruta relativa o absoluta de la muestra a auditar",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directorio destino para artefactos generados",
    )

    args = parser.parse_args()

    job_id = f"cli-{uuid.uuid4().hex[:8]}"
    mode = determine_operational_mode()
    source_repo = Path(args.sample).resolve()
    if not source_repo.is_dir():
        print(f"[ERROR] El directorio '{args.sample}' no existe.")
        sys.exit(1)

    artifacts_dir = Path(args.output_dir).resolve() if args.output_dir else (REPO_ROOT / "artifacts" / job_id)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("  CODEARCHAEOLOGIST × IBM BOB 2.0 — CLI DE AUDITORÍA FORENSE")
    print("=" * 75)
    print(f" • Job ID:         {job_id}")
    print(f" • Muestra:        {source_repo}")
    print(f" • Modo Operativo: {mode.upper()}")
    print("-" * 75)

    print("\n[+] Ejecutando auditoría forense determinista...")
    start_time = time.time()

    # Si hay sesión importada para FacturaYa, reutilizarla; si no, correr auditoría
    imported_path = REPO_ROOT / "contracts" / "fixtures" / "bob-session-facturaya.json"
    imported = imported_path if (imported_path.is_file() and "facturaya" in source_repo.name.lower()) else None

    dossier = run_evidence_audit(
        source_repo=source_repo,
        job_dir=artifacts_dir,
        imported_result=imported,
        job_id=job_id,
        execute_reference_cut=bool(imported),
    )

    total_duration = time.time() - start_time

    print("\n" + "=" * 75)
    print("  RESUMEN DE AUDITORÍA Y ARTEFACTOS GENERADOS")
    print("=" * 75)
    print(f" • Repositorio:       {dossier.repo_name}")
    print(f" • Citas Válidas:     {dossier.stats.evidence_valid}/{dossier.stats.evidence_total} ({dossier.stats.evidence_valid_ratio * 100:.1f}%)")
    print(f" • Hallazgos:         {len(dossier.findings)} aceptados, {len(dossier.rejected_findings)} rechazados")
    if dossier.recommendation and dossier.recommendation.recommended:
        rec = dossier.recommendation.recommended
        print(f" • Corte Recomendado: {rec.endpoint} (score: {rec.score})")
        print(f" • Por qué:           {rec.why}")
    if dossier.first_cut_pert:
        print(f" • Esfuerzo PERT:     {dossier.first_cut_pert.expected_days:.2f} días (heurística no calibrada)")
    print(f" • Duración Pipeline: {total_duration:.2f} segundos")
    print("-" * 75)
    print(" Artefactos exportados:")
    print(f"  [DOSSIER] {artifacts_dir / DOSSIER_FILE}")
    print(f"  [MEMO]    {artifacts_dir / BOARD_MEMO_FILE}")
    print("=" * 75)
    print("[OK] Auditoría completada exitosamente.")


if __name__ == "__main__":
    main()
