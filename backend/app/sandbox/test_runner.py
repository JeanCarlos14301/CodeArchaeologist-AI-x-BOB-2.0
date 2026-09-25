"""Ejecutor de Pruebas Pytest en Sandbox Aislado (D-07).

Ejecuta pytest en subproceso con:
- Timeout estricto de 60 segundos.
- Aislamiento de red (bloqueo de llamadas salientes mediante variables de entorno de proxy nulo).
- Parseo determinista de resultados por caso de prueba (PASS, FAIL, SKIPPED, duraciones, errores).
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
    """Ejecuta la suite de pruebas en el sandbox y extrae el reporte estructurado."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
    ]
    if test_path:
        cmd.append(test_path)

    # Entorno aislado sin acceso a red
    env = os.environ.copy()
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
                    error_message=f"Timeout de {timeout_seconds}s excedido durante la ejecución de pytest en sandbox.",
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
                    error_message=f"Fallo al invocar pytest: {str(e)}",
                )
            ],
        )

    # Parsear salidas de pytest
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
                error_msg = f"Fallo en {test_short_name}: revisar salida del trace."

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
        # Fallback si pytest corrió pero no se pudo parsear por líneas
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
