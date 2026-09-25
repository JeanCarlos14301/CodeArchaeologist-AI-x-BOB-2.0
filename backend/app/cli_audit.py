"""CLI de Auditoría y Diagnóstico Forense Local (CodeArchaeologist CLI).

Permite ejecutar el pipeline determinista completo de 11 etapas directamente
desde la terminal sin necesidad de levantar el servidor web:
    python -m backend.app.cli_audit --sample samples/facturaya-v1/

Genera y valida:
- Expediente JSON completo (DossierResult v1).
- Memorando Ejecutivo en Word (.docx).
- Reporte Interactivo Autónomo (.html).
- Presentación Ejecutiva (.pptx).
- Parche unificado de migración Strangler Fig (.diff).
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from backend.app.adapters.bob_adapter import determine_operational_mode
from backend.app.database import (
    create_job,
    get_job_events,
    get_job_result,
    init_db,
)
from backend.app.worker import get_artifacts_dir, run_pipeline_for_job

BASE_DIR = Path(__file__).resolve().parent.parent.parent


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
        "--source-type",
        type=str,
        default="demo",
        choices=["demo", "holdout", "zip"],
        help="Tipo de fuente (demo, holdout, zip)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        choices=["live", "imported", "example"],
        help="Modo de ejecución forzado (live, imported, example)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directorio destino para artefactos generados",
    )

    args = parser.parse_args()

    init_db()

    job_id = f"cli-{uuid.uuid4().hex[:8]}"
    effective_mode = args.mode or determine_operational_mode()

    print("=" * 75)
    print("  LEGACYLENS × IBM BOB 2.0 — CLI DE AUDITORÍA FORENSE")
    print("=" * 75)
    print(f" • Job ID:         {job_id}")
    print(f" • Muestra:        {args.sample}")
    print(f" • Tipo Fuente:    {args.source_type}")
    print(f" • Modo Operativo: {effective_mode.upper()}")
    print("-" * 75)

    create_job(
        job_id=job_id,
        source_type=args.source_type,
        execution_mode=effective_mode,
    )

    print("\n[+] Ejecutando las 11 etapas del pipeline determinista...")
    start_time = time.time()

    # Ejecutar pipeline
    run_pipeline_for_job(
        job_id=job_id,
        source_type=args.source_type,
        requested_mode=effective_mode,
    )

    total_duration = time.time() - start_time

    # Mostrar eventos
    events = get_job_events(job_id)
    for ev in events:
        if ev["status"] == "completed":
            dur = f"({ev['duration_ms']} ms)" if ev["duration_ms"] > 0 else ""
            print(f"  [OK] [Etapa {ev['stage']:2d}] {ev['stage_name']:<35} {dur}")
            if ev["message"]:
                print(f"        |-- {ev['message']}")

    # Obtener resultado
    result = get_job_result(job_id)
    if not result:
        print("\n[ERROR] El pipeline no generó un resultado válido.")
        sys.exit(1)

    artifacts_dir = get_artifacts_dir(job_id)
    if args.output_dir:
        custom_out = Path(args.output_dir)
        custom_out.mkdir(parents=True, exist_ok=True)
        for item in artifacts_dir.glob("*"):
            import shutil
            shutil.copy2(item, custom_out / item.name)
        artifacts_dir = custom_out

    print("\n" + "=" * 75)
    print("  RESUMEN DE AUDITORÍA Y ARTEFACTOS GENERADOS")
    print("=" * 75)
    snap = result.get("snapshot", {})
    val = result.get("validation_report", {})
    findings = result.get("findings", [])
    pert = result.get("pert_plan", [])
    total_pert = sum(p.get("pert_expected_days", 0) for p in pert)

    print(f" • Repositorio:       {snap.get('repo_name')} ({snap.get('total_files')} archivos, {snap.get('total_loc')} LOC)")
    print(f" • Fidelidad Citas:   {val.get('fidelity_ratio', 1.0) * 100:.1f}% ({val.get('valid_references')}/{val.get('total_references')} válidas)")
    print(f" • Hallazgos:         {len(findings)} detectados ({sum(1 for f in findings if f.get('severity') == 'CRITICAL')} críticos)")
    print(f" • Primer Corte:      {result.get('selected_first_cut')} (Strangler Fig)")
    print(f" • Esfuerzo PERT:     {total_pert:.1f} días laborables")
    print(f" • Duración Pipeline: {total_duration:.2f} segundos")
    print("-" * 75)
    print(" Artefactos exportados:")
    print(f"  [DOCX]  {artifacts_dir / 'board_memo.docx'}")
    print(f"  [HTML]  {artifacts_dir / 'report.html'}")
    print(f"  [PPTX]  {artifacts_dir / 'presentation.pptx'}")
    print(f"  [DIFF]  {artifacts_dir / 'migration.diff'}")
    print("=" * 75)
    print("[OK] Auditoría completada exitosamente.")


if __name__ == "__main__":
    main()
