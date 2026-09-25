---
name: code-audit
description: Comando de Bob para ejecutar la auditoría de evidencia (modo `evidence-auditor`) sobre el repositorio de entrada y emitir el expediente técnico en esquema v1 (`contracts/schema-v1.json`).
metadata:
  user-invocable: true
  disable-model-invocation: true
---
# /code-audit

Comando de Bob para ejecutar la auditoría de evidencia (modo `evidence-auditor`) sobre el repositorio de entrada y emitir el expediente técnico en esquema v1 (`contracts/schema-v1.json`).

## Uso
```bash
bob run --mode evidence-auditor /code-audit <ruta-del-repo>
```

## Argumentos
- `<ruta-del-repo>`: Ruta absoluta o relativa al directorio del repositorio a auditar.
- `--depth`: Nivel de profundidad (`fast` | `standard` | `deep`). Por defecto `standard`.

## Comportamiento
1. **Reconocimiento:** Identifica el stack técnico (Python, Flask, SQLite).
2. **Delegación Paralela:**
   - Auditoría de SQL e inyecciones (`legacy-sql-auditor`).
   - Mapeo de rutas y autenticación (`legacy-route-mapper`).
   - Trazabilidad de dependencias e import graph (`legacy-dependency-tracer`).
   - Escaneo de vulnerabilidades OWASP Top 10 (`legacy-security-scanner`).
3. **Validación de Evidencia:** Filtra cualquier afirmación que no cuente con archivo y líneas reales verificables.
4. **Salida:** Emite JSON conforme a `contracts/schema-v1.json` con `execution_mode: "live"`.
