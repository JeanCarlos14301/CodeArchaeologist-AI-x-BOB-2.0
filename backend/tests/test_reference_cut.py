from pathlib import Path

from app.sandbox.migration_runner import MODERN_INVOICES_API_CODE
from app.sandbox.reference_cut import run_reference_cut

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "samples" / "facturaya-v1"


def test_reference_cut_runs_real_tests_and_detects_broken_modern_code(tmp_path: Path) -> None:
    passing = run_reference_cut(SAMPLE, tmp_path / "passing")
    assert passing.status == "passed"
    assert {test.target for test in passing.tests} == {"legacy", "modern"}
    assert all(test.status == "passed" for test in passing.tests)
    assert (tmp_path / "passing" / "migration.diff").is_file()

    broken_code = MODERN_INVOICES_API_CODE.replace(
        'discount=f"{calc_discount:.2f}"',
        'discount="0.00"',
    )
    broken = run_reference_cut(SAMPLE, tmp_path / "broken", modern_code=broken_code)
    assert broken.status == "failed"
    assert any(test.target == "modern" and test.status == "failed" for test in broken.tests)
