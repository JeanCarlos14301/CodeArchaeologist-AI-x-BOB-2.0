"""Pytest runner in an isolated sandbox (D-07).

Runs pytest in a subprocess with:
- A strict 60-second timeout.
- Network isolation (outgoing calls blocked through null proxy environment variables).
- Deterministic parsing of results per test case (PASS, FAIL, SKIPPED, durations, errors).
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from backend.app.models import CharacterizationTestCase, CharacterizationTestReport


def run_pytest_in_sandbox(
    sandbox_dir: Path,
    test_path: Optional[str] = None,
    target_endpoint: str = "GET /invoices/{id}",
    timeout_seconds: int = 60,
) -> CharacterizationTestReport:
    """Runs the test suite in the sandbox and extracts the structured report."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        # Keep pytest's temp dirs and cache inside the sandbox: the global temp dir
        # (e.g. %TEMP%\pytest-of-<user>) can be locked or shared, which turns every
        # tmp_path test into an error unrelated to the code under test.
        f"--basetemp={(sandbox_dir / '.pytest-tmp').resolve()}",
        "-p", "no:cacheprovider",
    ]
    if test_path:
        cmd.append(test_path)

    # Isolated environment without network access
    env = os.environ.copy()
    # The code under test must never read server credentials (BOB_API_KEY, tokens...).
    for key in list(env):
        if any(marker in key.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            del env[key]
    env["HTTP_PROXY"] = "http://127.0.0.1:9/"
    env["HTTPS_PROXY"] = "http://127.0.0.1:9/"
    env["ALL_PROXY"] = "http://127.0.0.1:9/"
    env["NO_PROXY"] = ""
    env["PYTHONPATH"] = f"{sandbox_dir.resolve()}{os.pathsep}{env.get('PYTHONPATH', '')}"

    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(sandbox_dir.resolve()),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
        total_duration_ms = round((time.time() - start_time) * 1000, 2)
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode

    except subprocess.TimeoutExpired:
        return CharacterizationTestReport(
            total_tests=1,
            passed_count=0,
            failed_count=1,
            target_endpoint=target_endpoint,
            all_passed=False,
            test_cases=[
                CharacterizationTestCase(
                    name="suite_execution_timeout",
                    target_endpoint=target_endpoint,
                    test_type="sandbox_execution",
                    status="FAIL",
                    duration_ms=timeout_seconds * 1000,
                    error_message=f"Timeout of {timeout_seconds}s exceeded while running pytest in the sandbox.",
                )
            ],
        )
    except Exception as e:
        return CharacterizationTestReport(
            total_tests=1,
            passed_count=0,
            failed_count=1,
            target_endpoint=target_endpoint,
            all_passed=False,
            test_cases=[
                CharacterizationTestCase(
                    name="sandbox_runner_error",
                    target_endpoint=target_endpoint,
                    test_type="sandbox_execution",
                    status="FAIL",
                    duration_ms=0.0,
                    error_message=f"Failed to invoke pytest: {str(e)}",
                )
            ],
        )

    # Parse pytest output
    # Ej: tests/test_invoice_contract.py::test_first_invoice_exact_contract PASSED
    test_cases: List[CharacterizationTestCase] = []
    lines = stdout.splitlines()

    for line in lines:
        match = re.search(r"([\w_/-]+\.py::[\w_]+)\s+(PASSED|FAILED|SKIPPED|XFAIL)", line)
        if match:
            test_full_name = match.group(1)
            outcome = match.group(2)
            test_short_name = test_full_name.split("::")[-1]

            status = "PASS" if outcome == "PASSED" else ("FAIL" if outcome == "FAILED" else "SKIPPED")
            error_msg = None
            if status == "FAIL":
                error_msg = f"Failure in {test_short_name}: check the trace output."

            test_type = "contract"
            if "security" in test_short_name or "auth" in test_short_name or "foreign" in test_short_name:
                test_type = "security"
            elif "rule" in test_short_name or "discount" in test_short_name or "rounding" in test_short_name:
                test_type = "business_rule"

            test_cases.append(
                CharacterizationTestCase(
                    name=test_short_name,
                    target_endpoint=target_endpoint,
                    test_type=test_type,
                    status=status,
                    duration_ms=round(total_duration_ms / max(1, len(test_cases) + 1), 2),
                    error_message=error_msg,
                )
            )

    if not test_cases:
        # Fallback when pytest ran but its output could not be parsed line by line
        status = "PASS" if exit_code == 0 else "FAIL"
        test_cases.append(
            CharacterizationTestCase(
                name="test_endpoint_characterization_suite",
                target_endpoint=target_endpoint,
                test_type="contract",
                status=status,
                duration_ms=total_duration_ms,
                error_message=None if status == "PASS" else stdout[-500:],
            )
        )

    passed_count = sum(1 for tc in test_cases if tc.status == "PASS")
    failed_count = sum(1 for tc in test_cases if tc.status == "FAIL")

    return CharacterizationTestReport(
        total_tests=len(test_cases),
        passed_count=passed_count,
        failed_count=failed_count,
        target_endpoint=target_endpoint,
        test_cases=test_cases,
        all_passed=(failed_count == 0 and passed_count > 0),
    )
