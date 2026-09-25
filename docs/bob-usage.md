# Registro de uso e integración de IBM Bob 2.0

Este documento registra las sesiones de invocación de IBM Bob Shell (`bob run`), los modos personalizados habilitados en `.bob/custom_modes.yaml` y los patrones de orquestación multi-agente implementados por Felipe para la hackathon.

## Registro de Sesiones

| Fecha | Integrante | Modo / Agente | Tarea | Resultado |
|---|---|---|---|---|
| 2026-09-24 19:30 | Felipe | `evidence-auditor` | F-01 / F-02: Calibración de prompt defense y extracción schema v1 | Validado: cero alucinaciones en repo demo |
| 2026-09-24 20:15 | Felipe | `migration-architect` | F-04: Formulación de 3 cortes Strangler Fig en Flask demo | Opciones calculadas con estimación PERT y blast radius |
| 2026-09-24 20:50 | Felipe | `contract-keeper` | F-05: Generación de suite pytest de caracterización para `/invoices/{id}` | 100% verde en legacy endpoint |
| 2026-09-24 21:20 | Felipe | `polyglot-architect` | F-10: Mapeo de conceptos FastAPI → NestJS y contratos OpenAPI | Matriz de traducción Zod/class-validator completada |
| 2026-09-24 21:40 | Felipe | `blast-radius-guard` | F-11: Simulación de fallo en cascada de `db_pool.py` antes de PR | CBRS: 78/100 (Veredicto RED_BLOCK por mutación compartida) |
| 2026-09-24 21:55 | Felipe | `code-skeptic` | F-12: Debate adversarial contra propuesta de migración FastAPI | 3 vulnerabilidades de concurrencia y rollback detectadas |
| 2026-09-24 22:15 | Felipe | `git-archaeologist` | F-13: Minería PyDriller de commits y matriz de hotspots | Archivo `legacy_db.py` identificado como mayor churn (82%) |
| 2026-09-25 13:20 | Felipe | `ask`, `evidence-auditor` | F-01 / F-02: instalación de Bob Shell 2.0.5 y prueba de humo con API key vía `BobAdapter` | `status: success`, ~0.046 bobcoins por llamada; modo personalizado cargado desde `.bob/custom_modes.yaml` |
| 2026-09-25 13:50 | Felipe | `evidence-auditor` | F-03: etapas 2-3 sobre FacturaYa (`python -m app.pipeline.run_audit`) | 13 hallazgos, 16/16 evidencias válidas tras el validador; 6/6 hallazgos esperados detectados y 0 sobre el control EF-7; 0,57 bobcoins, 87 s |
| 2026-09-25 13:45 | Felipe | `evidence-auditor` + subagentes | Integración de `.bob/agents` y `.bob/skills`: auditoría live con delegación | Delegó en `legacy-sql-auditor`, `legacy-security-scanner` y `legacy-dependency-tracer` (log de Bob); 12/12 hallazgos y 18/18 evidencias válidas; 1,13 bobcoins, 189 s |

## Modos Personalizados Registrados (`.bob/custom_modes.yaml`)

| Slug | Nombre | Permisos | Objetivo |
|---|---|---|---|
| `evidence-auditor` | Evidence Auditor | `read` | Inspección forense con evidencia de archivo y línea (schema v1). |
| `migration-architect` | Migration Architect | `read` | Selección del primer corte y 3 opciones de migración Strangler Fig. |
| `contract-keeper` | Contract Keeper | `read, edit` | Creación de pruebas de caracterización golden-master con pytest. |
| `strangler-surgeon` | Strangler Surgeon | `read, edit, command` | Implementación del nuevo corte moderno bajo `modern/` detrás de fachada. |
| `board-narrator` | Board Narrator | `read` | Redacción del memo ejecutivo para la junta sin inventar cifras. |
| `polyglot-architect` | Polyglot Architect | `read` | Mapeo de tipos y patrones cruzados (FastAPI ↔ NestJS ↔ Spring Boot). |
| `blast-radius-guard` | Blast Radius Guard | `read` | Simulación estática pre-PR de radio de explosión y fallas en cascada. |
| `code-skeptic` | Code Skeptic | `read` | Tribunal adversarial para estresar y validar propuestas técnicas. |
| `git-archaeologist` | Git Archaeologist | `read, command` | Minería forense de repositorios git con PyDriller. |

## Invocación Segura desde Python (Subprocess)

De acuerdo con las reglas de `AGENTS.md`, la invocación de Bob se realiza de forma estrictamente determinista mediante lista de argumentos, sin `shell=True`:

```python
import subprocess
from typing import Dict, Any

def run_bob_mode(mode: str, input_context_file: str, output_file: str) -> subprocess.CompletedProcess:
    """
    Invoca a IBM Bob en un modo específico pasando contexto seguro.
    Nunca se concatena texto de usuario directamente en la terminal.
    """
    cmd = [
        "bob",
        "run",
        "--mode", mode,
        "--context", input_context_file,
        "--output", output_file,
        "--non-interactive"
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=True)
```

## Patrones de Orquestación Multi-Agente

### 1. Tribunal Adversarial (Dialéctica de 4 Rondas)
```
Proponente: migration-architect / polyglot-architect
        │
        ▼ (Ronda 1: Propuesta técnica con supuestos y tests)
Fiscal Adversarial: code-skeptic
        │
        ▼ (Ronda 2: Objeciones por concurrencia, leaks y rollback)
Proponente: Rebuttal con pruebas formales y modificaciones
        │
        ▼ (Ronda 3: Defensa y concesiones)
Tribunal: Veredicto vinculante (UNANIMOUS_PASS / CONDITIONAL / BLOCK)
```

### 2. Puerta Shift-Left Pre-PR (Blast Radius Simulator)
```
Desarrollador / Agente genera cambio
        │
        ▼
blast-radius-simulator:
  1. Extrae símbolos tocados en el AST
  2. Traza grafo transitivo de llamadas
  3. Evalúa impacto en base de datos
  4. Calcula Composite Blast Radius Score (CBRS)
        │
        ├─ CBRS < 25  ──► GREEN (Aprobación estándar)
        ├─ 25 <= CBRS < 60 ──► YELLOW (Requiere tests adicionales)
        └─ CBRS >= 60 ──► RED (BLOQUEO preventivo automático)
```


## Instalación y ejecución de Bob Shell

```bash
curl -fsSL https://bob.ibm.com/download/bobshell.sh | bash -s -- --pm npm   # requiere Node 24+
cp .env.example .env    # y rellena BOB_API_KEY (scope: Inference)
```

La primera ejecución exige aceptar la licencia de IBM (`bob` en interactivo, o `--accept-license`).
El pipeline invoca a Bob solo a través de `backend/app/adapters/bob_adapter.py`:

```python
from pathlib import Path
from app.adapters.bob_adapter import BobAdapter
result = BobAdapter(Path("samples/facturaya-v1")).run("evidence-auditor", prompt)
```

Pruebas: `cd backend && pytest` (la prueba `live` se omite si no hay `bob` o `BOB_API_KEY`).

### Auditoría de evidencia de punta a punta (etapas 2 y 3)

```bash
cd backend
python -m app.pipeline.run_audit ../samples/facturaya-v1/samples/facturaya-v1          # live
python -m app.pipeline.run_audit <repo> --import ../contracts/fixtures/bob-evidence-auditor-facturaya.json  # imported
```

El repo se copia a `artifacts/jobs/<id>/workspace` sin `evaluation/` ni `expected-findings*.json`,
de modo que Bob nunca ve el material de evaluación. La salida queda en `artifacts/jobs/<id>/dossier.json`.

### Cómo descubre Bob Shell los activos del proyecto (verificado en 2.0.5)
- Subagentes: `.bob/agents/*.md`. Frontmatter línea a línea: `name`, `description` en **una sola línea**,
  `groups` (lista), opcional `modelTier` (`fast|premium|ultra|explorer`). **`model:` hace que Bob descarte el agente.**
- Skills: `.bob/skills/<nombre>/SKILL.md`, con `name` igual a la carpeta.
- Comandos: Bob convierte `.bob/commands/*.md` en `.bob/skills/<nombre>/` al arrancar (y pisa skills homónimas),
  por eso los comandos viven directamente como skills con `user-invocable: true`.
- Grupos válidos en modos y subagentes: `read, edit, execute, browser, mcp, skill, todo, subagent, mode`.
  Un modo necesita `subagent` para delegar y `skill` para activar skills.
- Bob también carga skills globales de `~/.bob/skills`, `~/.agents/skills` y `~/.claude/skills`.
