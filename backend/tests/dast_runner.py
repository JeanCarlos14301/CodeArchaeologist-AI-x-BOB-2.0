"""DAST (Dynamic Application Security Testing) script using curl.

Sends real HTTP requests to the local server (127.0.0.1:8088):
1. Functional validation of the base endpoints (/health, /api/samples, /api/audits).
2. Verification of GET /api/audits/{id}/migration with the recommendation and PERT.
3. Security and robustness tests:
   - Access control and unauthorized upload (403 when locked, 400 for a non-ZIP when open).
   - Path traversal injection (../../etc/passwd, ..\\..\\Windows\\win.ini).
   - Parameter injection (SQLi / ' OR 1=1 --).
   - Fuzzing of disallowed HTTP methods (405).
   - Handling of missing IDs (404).
   - Malformed payloads (422).
"""

import json
import subprocess
import sys
import time

BASE_URL = "http://127.0.0.1:8088"


def curl(args: list[str]) -> tuple[int, str]:
    """Runs the system curl.exe and returns the HTTP code and the response body."""
    cmd = ["curl.exe", "-s", "-w", "\n%{http_code}"] + args
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    parts = res.stdout.rsplit("\n", 1)
    if len(parts) == 2:
        body = parts[0]
        code = int(parts[1].strip() or "0")
    else:
        body = res.stdout
        code = 0
    return code, body


def run_dast() -> None:
    print("=" * 70)
    print("STARTING THE STRICT DAST SUITE WITH CURL (http://127.0.0.1:8088)")
    print("=" * 70)
    passes = 0
    total = 0

    def assert_check(description: str, condition: bool, details: str = ""):
        nonlocal passes, total
        total += 1
        if condition:
            passes += 1
            print(f"[PASS] {description}")
        else:
            print(f"[FAIL] {description} -> {details}")
            sys.exit(1)

    # 1. Health check
    code, body = curl([f"{BASE_URL}/health"])
    assert_check("1. GET /health answers HTTP 200", code == 200, f"code={code}")
    data = json.loads(body)
    assert_check("1b. /health status is 'ok'", data.get("status") == "ok")

    # 2. Samples endpoint
    code, body = curl([f"{BASE_URL}/api/samples"])
    assert_check("2. GET /api/samples answers HTTP 200", code == 200, f"code={code}")
    samples = json.loads(body)
    assert_check("2b. Sample 'facturaya-v1' available", any(s.get("id") == "facturaya-v1" for s in samples))

    # 3. Start the FacturaYa sample audit
    code, body = curl([
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", '{"sample": "facturaya-v1", "execution_mode": "imported"}',
        f"{BASE_URL}/api/audits"
    ])
    assert_check("3. POST /api/audits returns 202 Accepted", code == 202, f"code={code}, body={body}")
    job = json.loads(body)
    job_id = job.get("id")
    assert_check("3b. Returns a valid job ID", bool(job_id), f"body={body}")

    # 4. Wait for the analysis to finish
    print(f"[*] Waiting for job {job_id}...")
    deadline = time.monotonic() + 45
    status = "running"
    while time.monotonic() < deadline:
        code, body = curl([f"{BASE_URL}/api/audits/{job_id}"])
        if code == 200:
            job_info = json.loads(body).get("job", {})
            status = job_info.get("status")
            if status in ("done", "failed"):
                break
        time.sleep(0.5)

    assert_check("4. Job ends in state 'done'", status == "done", f"status={status}")

    # 5. Validation of the migration endpoint
    code, body = curl([f"{BASE_URL}/api/audits/{job_id}/migration"])
    assert_check("5. GET /api/audits/{id}/migration answers 200 OK", code == 200, f"code={code}")
    migration = json.loads(body)

    # Validate candidates and ranking
    candidates = migration.get("candidates", [])
    assert_check("5b. Contains 10 evaluated candidate routes", len(candidates) == 10, f"len={len(candidates)}")
    scores = [c["score"] for c in candidates]
    assert_check("5c. Candidates sorted by score, descending", scores == sorted(scores, reverse=True))

    recommended = migration.get("recommended")
    assert_check("5d. Recommended candidate present with a positive score", recommended and recommended.get("score") > 0)

    no_start = migration.get("do_not_start_here")
    assert_check("5e. 'Do not start here' identified with high risk", no_start and no_start.get("risk") > 15.0)

    waves = migration.get("waves", [])
    assert_check("5f. Roadmap split into 3 Strangler Fig waves", len(waves) == 3, f"len={len(waves)}")

    pert = migration.get("first_cut_pert")
    assert_check("5g. First-cut PERT includes the uncalibrated heuristic warning",
                 pert and any("Uncalibrated heuristic estimate" in a for a in pert.get("assumptions", [])))

    # 6. Security DAST: access control on upload
    code, body = curl([
        "-X", "POST",
        "-F", "zip_file=@backend/app/main.py",
        "-H", "X-Live-Token: fake-invalid-token",
        f"{BASE_URL}/api/audits/upload"
    ])
    assert_check("6. POST /api/audits/upload with a bad token or a non-ZIP is rejected (HTTP 403/400)", code in (400, 403), f"code={code}, body={body}")

    # 7. Security DAST: path traversal
    traversals = [
        "../../../../etc/passwd",
        "..\\..\\..\\Windows\\win.ini",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "/etc/shadow",
    ]
    for trav in traversals:
        code, body = curl([f"{BASE_URL}/api/audits/{job_id}/source?path={trav}"])
        assert_check(f"7. Path traversal prevented for '{trav}' (HTTP {code})", code in (400, 404, 422), f"code={code}")

    # 8. Security DAST: audit ID with SQL injection / invalid characters
    import urllib.parse
    injections = [
        "' OR 1=1 --",
        "'; DROP TABLE jobs; --",
        "../../jobs",
        "<script>alert(1)</script>",
    ]
    for inj in injections:
        quoted = urllib.parse.quote(inj)
        code, body = curl([f"{BASE_URL}/api/audits/{quoted}/migration"])
        assert_check(f"8. Malicious job_id input rejected with 404/400 '{inj}' (HTTP {code})", code in (404, 400), f"code={code}")

    # 9. Security DAST: disallowed methods (405)
    code, body = curl([
        "-X", "POST",
        f"{BASE_URL}/api/audits/{job_id}/migration"
    ])
    assert_check("9. POST on the migration endpoint returns 405 Method Not Allowed", code == 405, f"code={code}")

    # 10. Security DAST: malformed JSON payload / invalid schema
    code, body = curl([
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", '{"sample": "facturaya-v1", "execution_mode": "invalid-mode-123"}',
        f"{BASE_URL}/api/audits"
    ])
    assert_check("10. Payload with an invalid enum rejected with 422 Unprocessable Entity", code == 422, f"code={code}, body={body}")

    print("=" * 70)
    print(f"DAST RESULT: {passes}/{total} CHECKS PASSED (100% OK)")
    print("=" * 70)


if __name__ == "__main__":
    run_dast()
