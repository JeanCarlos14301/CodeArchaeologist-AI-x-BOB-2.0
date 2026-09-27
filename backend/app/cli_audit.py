"""Forensic audit CLI (CodeArchaeologist CLI).

Runs the deterministic pipeline and the forensic audit straight from the terminal,
without starting the web server:
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

    parser = argparse.ArgumentParser(description="CodeArchaeologist CLI — forensic audit and modernization")
    parser.add_argument(
        "--sample",
        type=str,
        default="samples/facturaya-v1",
        help="Relative or absolute path of the sample to audit",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Target directory for the generated artifacts",
    )

    args = parser.parse_args()

    job_id = f"cli-{uuid.uuid4().hex[:8]}"
    mode = determine_operational_mode()
    source_repo = Path(args.sample).resolve()
    if not source_repo.is_dir():
        print(f"[ERROR] The directory '{args.sample}' does not exist.")
        sys.exit(1)

    artifacts_dir = Path(args.output_dir).resolve() if args.output_dir else (REPO_ROOT / "artifacts" / job_id)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("  CODEARCHAEOLOGIST × IBM BOB 2.0 — FORENSIC AUDIT CLI")
    print("=" * 75)
    print(f" • Job ID:         {job_id}")
    print(f" • Sample:         {source_repo}")
    print(f" • Mode:           {mode.upper()}")
    print("-" * 75)

    print("\n[+] Running the deterministic forensic audit...")
    start_time = time.time()

    # If there is a recorded session for FacturaYa, reuse it; otherwise run the audit
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
    print("  AUDIT SUMMARY AND GENERATED ARTIFACTS")
    print("=" * 75)
    print(f" • Repository:        {dossier.repo_name}")
    print(f" • Valid citations:   {dossier.stats.evidence_valid}/{dossier.stats.evidence_total} ({dossier.stats.evidence_valid_ratio * 100:.1f}%)")
    print(f" • Findings:          {len(dossier.findings)} accepted, {len(dossier.rejected_findings)} rejected")
    if dossier.recommendation and dossier.recommendation.recommended:
        rec = dossier.recommendation.recommended
        print(f" • Recommended cut:   {rec.endpoint} (score: {rec.score})")
        print(f" • Why:               {rec.why}")
    if dossier.first_cut_pert:
        print(f" • PERT effort:       {dossier.first_cut_pert.expected_days:.2f} days (uncalibrated heuristic)")
    print(f" • Pipeline duration: {total_duration:.2f} seconds")
    print("-" * 75)
    print(" Exported artifacts:")
    print(f"  [DOSSIER] {artifacts_dir / DOSSIER_FILE}")
    print(f"  [MEMO]    {artifacts_dir / BOARD_MEMO_FILE}")
    print("=" * 75)
    print("[OK] Audit completed successfully.")


if __name__ == "__main__":
    main()
