"""Script de pruebas DAST (Dynamic Application Security Testing) mediante curl.

Ejecuta peticiones HTTP reales contra el servidor local (127.0.0.1:8088):
1. Validación funcional de endpoints base (/health, /api/samples, /api/audits).
2. Verificación del endpoint GET /api/audits/{id}/migration con recomendación y PERT.
3. Pruebas de seguridad y robustez:
   - Control de acceso y subida no autorizada (403).
   - Inyección de Path Traversal (../../etc/passwd, ..\\..\\Windows\\win.ini).
   - Inyección en parámetros (SQLi / ' OR 1=1 --).
   - Fuzzing de métodos HTTP no permitidos (405).
   - Manejo de IDs inexistentes (404).
   - Cargas útiles malformadas (422).
"""

import json
import subprocess
import sys
import time

BASE_URL = "http://127.0.0.1:8088"


def curl(args: list[str]) -> tuple[int, str]:
    """Ejecuta curl.exe del sistema y retorna el código HTTP y el cuerpo de respuesta."""
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
    print("INICIANDO SUITE DAST EXIGENTE CON CURL (http://127.0.0.1:8088)")
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
    assert_check("1. GET /health responde HTTP 200", code == 200, f"code={code}")
    data = json.loads(body)
    assert_check("1b. /health status es 'ok'", data.get("status") == "ok")

    # 2. Samples endpoint
    code, body = curl([f"{BASE_URL}/api/samples"])
    assert_check("2. GET /api/samples responde HTTP 200", code == 200, f"code={code}")
    samples = json.loads(body)
    assert_check("2b. Muestra 'facturaya-v1' disponible", any(s.get("id") == "facturaya-v1" for s in samples))

    # 3. Iniciar auditoría de muestra FacturaYa
    code, body = curl([
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", '{"sample": "facturaya-v1", "execution_mode": "imported"}',
        f"{BASE_URL}/api/audits"
    ])
    assert_check("3. POST /api/audits devuelve 202 Accepted", code == 202, f"code={code}, body={body}")
    job = json.loads(body)
    job_id = job.get("id")
    assert_check("3b. Retorna un job ID válido", bool(job_id), f"body={body}")

    # 4. Esperar finalización del análisis
    print(f"[*] Esperando procesamiento del job {job_id}...")
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

    assert_check("4. Job finaliza en estado 'done'", status == "done", f"status={status}")

    # 5. Validación del endpoint de migración
    code, body = curl([f"{BASE_URL}/api/audits/{job_id}/migration"])
    assert_check("5. GET /api/audits/{id}/migration responde 200 OK", code == 200, f"code={code}")
    migration = json.loads(body)

    # Validar candidatos y ranking
    candidates = migration.get("candidates", [])
    assert_check("5b. Contiene 10 rutas candidatas evaluadas", len(candidates) == 10, f"len={len(candidates)}")
    scores = [c["score"] for c in candidates]
    assert_check("5c. Candidatos ordenados descendentemente por score", scores == sorted(scores, reverse=True))

    recommended = migration.get("recommended")
    assert_check("5d. Candidato recomendado presente y con score positivo", recommended and recommended.get("score") > 0)

    no_start = migration.get("do_not_start_here")
    assert_check("5e. 'No empezar por aquí' identificado con alto riesgo", no_start and no_start.get("risk") > 15.0)

    waves = migration.get("waves", [])
    assert_check("5f. Hoja de ruta dividida en 3 olas Strangler Fig", len(waves) == 3, f"len={len(waves)}")

    pert = migration.get("first_cut_pert")
    assert_check("5g. PERT del primer corte incluye aviso heurístico uncalibrated",
                 pert and any("Estimación heurística, no calibrada" in a for a in pert.get("assumptions", [])))

    # 6. DAST de Seguridad: Control de acceso en Upload
    code, body = curl([
        "-X", "POST",
        "-F", "zip_file=@backend/app/main.py",
        "-H", "X-Live-Token: token-falso-invalido",
        f"{BASE_URL}/api/audits/upload"
    ])
    assert_check("6. POST /api/audits/upload sin token válido es rechazado (HTTP 403/503)", code in (403, 503), f"code={code}, body={body}")

    # 7. DAST de Seguridad: Path Traversal
    traversals = [
        "../../../../etc/passwd",
        "..\\..\\..\\Windows\\win.ini",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "/etc/shadow",
    ]
    for trav in traversals:
        code, body = curl([f"{BASE_URL}/api/audits/{job_id}/source?path={trav}"])
        assert_check(f"7. Path traversal prevenido para '{trav}' (HTTP {code})", code in (400, 404, 422), f"code={code}")

    # 8. DAST de Seguridad: ID de auditoría con Inyección SQL / caracteres no válidos
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
        assert_check(f"8. Entrada maliciosa en job_id rechazada con 404/400 '{inj}' (HTTP {code})", code in (404, 400), f"code={code}")

    # 9. DAST de Seguridad: Métodos no permitidos (405)
    code, body = curl([
        "-X", "POST",
        f"{BASE_URL}/api/audits/{job_id}/migration"
    ])
    assert_check("9. POST en endpoint de migración devuelve 405 Method Not Allowed", code == 405, f"code={code}")

    # 10. DAST de Seguridad: Carga útil JSON malformada / esquema inválido
    code, body = curl([
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", '{"sample": "facturaya-v1", "execution_mode": "modo-invalido-123"}',
        f"{BASE_URL}/api/audits"
    ])
    assert_check("10. Payload con enum inválido rechazado con 422 Unprocessable Entity", code == 422, f"code={code}, body={body}")

    print("=" * 70)
    print(f"RESULTADO DAST: {passes}/{total} PRUEBAS EXITOSAS (100% OK)")
    print("=" * 70)


if __name__ == "__main__":
    run_dast()
