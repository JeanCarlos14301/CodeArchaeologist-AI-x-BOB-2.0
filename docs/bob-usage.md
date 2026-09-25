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
