# Registro de uso e integración de IBM Bob 2.0

Este documento registra las sesiones de invocación de IBM Bob Shell (`bob run`), los modos personalizados habilitados en `.bob/custom_modes.yaml` y los patrones de orquestación multi-agente implementados por Felipe para la hackathon.

## Registro de Sesiones

Cada fila indica su respaldo. Sin `bob-result.json` o captura versionados, el resultado no es una medición.

| Fecha | Integrante | Modo / Agente | Tarea | Resultado | Respaldo |
|---|---|---|---|---|---|
| 2026-09-24 19:30 | Felipe | `evidence-auditor` | F-01 / F-02: Calibración de prompt defense y extracción schema v1 | Afirmación sin verificar; no debe citarse como resultado medido. Original: Validado: cero alucinaciones en repo demo | Sin artefacto verificable: no hay `bob-result.json` ni captura versionados |
| 2026-09-24 20:15 | Felipe | `migration-architect` | F-04: Formulación de 3 cortes Strangler Fig en Flask demo | Afirmación sin verificar; no debe citarse como resultado medido. Original: Opciones calculadas con estimación PERT y blast radius | Sin artefacto verificable: no hay `bob-result.json` ni captura versionados |
| 2026-09-24 20:50 | Felipe | `contract-keeper` | F-05: Generación de suite pytest de caracterización para `/invoices/{id}` | Afirmación sin verificar; no debe citarse como resultado medido. Original: 100% verde en legacy endpoint | Sin artefacto verificable: no hay `bob-result.json` ni captura versionados |
| 2026-09-24 21:20 | Felipe | `polyglot-architect` | F-10: Mapeo de conceptos FastAPI → NestJS y contratos OpenAPI | Afirmación sin verificar; no debe citarse como resultado medido. Original: Matriz de traducción Zod/class-validator completada | Sin artefacto verificable: no hay `bob-result.json` ni captura versionados |
| 2026-09-24 21:40 | Felipe | `blast-radius-guard` | F-11: diseño de simulación sobre un archivo hipotético `db_pool.py` | **Diseño, no ejecutado.** El archivo no existe en FacturaYa y no se presenta como resultado medido. | Ninguno: diseño, no ejecutado |
| 2026-09-24 21:55 | Felipe | `code-skeptic` | F-12: Debate adversarial contra propuesta de migración FastAPI | Afirmación sin verificar; no debe citarse como resultado medido. Original: 3 vulnerabilidades de concurrencia y rollback detectadas | Sin artefacto verificable: no hay `bob-result.json` ni captura versionados |
| 2026-09-24 22:15 | Felipe | `git-archaeologist` | F-13: diseño de minería sobre un archivo hipotético `legacy_db.py` | **Diseño, no ejecutado.** El archivo no existe en FacturaYa y no hay artefacto que respalde una cifra de churn. | Ninguno: diseño, no ejecutado |
| 2026-09-25 13:20 | Felipe | `ask`, `evidence-auditor` | F-01 / F-02: instalación de Bob Shell 2.0.5 y prueba de humo con API key vía `BobAdapter` | Afirmación sin verificar; no debe citarse como resultado medido. Original: `status: success`, ~0.046 bobcoins por llamada; modo personalizado cargado desde `.bob/custom_modes.yaml` | Sin artefacto verificable: no hay `bob-result.json` ni captura versionados |
| 2026-09-25 13:45 | Felipe | `evidence-auditor` + subagentes | Integración de `.bob/agents` y `.bob/skills`: auditoría live con delegación | Afirmación sin verificar; no debe citarse como resultado medido. Original: Delegó en `legacy-sql-auditor`, `legacy-security-scanner` y `legacy-dependency-tracer` (log de Bob); 12/12 hallazgos y 18/18 evidencias válidas; 1,13 bobcoins, 189 s | Sin artefacto verificable: no hay `bob-result.json` ni captura versionados |
| 2026-09-25 13:50 | Felipe | `evidence-auditor` | F-03: etapas 2-3 sobre FacturaYa (`python -m app.pipeline.run_audit`) | 13 hallazgos, 16/16 evidencias válidas tras el validador; 6/6 hallazgos esperados detectados y 0 sobre el control EF-7; 0,57 bobcoins, 87 s | `contracts/fixtures/bob-evidence-auditor-facturaya.json` (respuesta cruda de Bob). Reproducible: `python evaluation/score.py` sobre el dossier que sale de importarla da 6/6, 0 falsos positivos |
| 2026-09-25 15:22 | Jean | `evidence-auditor` (live, primera corrida desde un checkout limpio, tras instalar Bob Shell 2.0.5 + Node 24) | Auditoría real de `facturaya-v1` desde la interfaz | job `02833a24a7a7`: 13 hallazgos reportados, 12 validados, 16/17 evidencias válidas (94%), 1,14 bobcoins, 120 s. Contra `expected-findings.json`: 5/6 hallazgos esperados detectados y validados, 1 (`EF-3`, descuento duplicado) detectado por Bob pero rechazado por el validador (evidencia de `reports.py` no calzó), 0 falsos positivos sobre el control `EF-7`. Detalle en `evaluation/README.md`. Artefactos completos (workspace copiado, `bob-result.json`, `dossier.json`) en `artifacts/jobs/02833a24a7a7/` (no versionado; queda en la máquina de Jean) | Artefactos locales, no versionados (`artifacts/jobs/`) |
| 2026-09-26 00:09 | Felipe | `ask` (`--format stream-json`) | Prueba del formato de eventos en tiempo real sobre dos archivos | Emite `message`, `tool_use`, `tool_result` y `result`; 0,14 bobcoins | Artefactos locales, no versionados (`artifacts/jobs/`) |
| 2026-09-26 00:09 | Felipe | `evidence-auditor` (`--resume`) | Diagnóstico del fallo de `upload:proyecto_ciber-main.zip` (job `2f944b585cdb`) | Bob agotó el tope de 5 bobcoins (sus 4 subagentes gastaron 3,89) sin entregar el JSON; «No files found» era su última búsqueda. Reanudar la sesión entregó el JSON por 0,17 bobcoins (15 hallazgos, 13 validados). No se publicó: el sandbox excluía `tests/` y Bob reportó «sin pruebas» en falso (corregido) | Artefactos locales, no versionados (`artifacts/jobs/`) |
| 2026-09-26 00:18 | Felipe | `evidence-auditor` (live, stream) | Primera auditoría con actividad en vivo (job `6a3ed667018e`) | El servicio de inferencia cortó el stream (`read ETIMEDOUT`) a los 154 s. La sesión, localizada por su workspace, se reanudó y entregó un JSON válido (0,68 bobcoins en total). Motivó el rescate automático | Artefactos locales, no versionados (`artifacts/jobs/`) |
| 2026-09-26 00:25 | Felipe | `evidence-auditor` + 4 subagentes (live, stream) | Grabación de la vitrina (job `0234884643c5`) | Delegó en paralelo en `legacy-sql-auditor`, `legacy-route-mapper`, `legacy-security-scanner` y `legacy-dependency-tracer` (0,04–0,11 bobcoins cada uno); 12/12 hallazgos, 14/14 evidencias válidas, primer corte 3/3; 1,15 bobcoins, 165 s. Contra `expected-findings.json`: 5/6 (EF-3 detectado como F-7 pero citando las constantes, no el cálculo). Es la sesión que reproduce la vitrina | Artefactos locales, no versionados (`artifacts/jobs/`) |
| 2026-09-26 00:30 | Felipe | `evidence-auditor` (live, stream) | Corrida con la regla «citar la línea donde ocurre el problema» (job `b7424d9733a6`) | Bob no delegó (leyó los 12 archivos); 10/10 hallazgos, 13/13 evidencias; 1,44 bobcoins, 126 s. 5/6: detectó EF-3 y no reportó EF-2 (variabilidad entre corridas) | Artefactos locales, no versionados (`artifacts/jobs/`) |

### Medición contra la verdad de referencia
`python evaluation/score.py <dossier.json>` aplica una única regla: un esperado es acierto si un hallazgo **validado** solapa sus líneas
en el mismo archivo; los rechazados no cuentan. Con la única corrida versionada (13:50 del 25/09) da 6/6. Los **5/6** que citan
las corridas de Jean (`02833a24a7a7`) y de Felipe (`b7424d9733a6`, `0234884643c5`) **no se pueden reproducir** con datos del repo: sus
`dossier.json` no están versionados. Para respaldarlos hay que subir esos expedientes (sin credenciales) a `contracts/fixtures/`.

## Modos Personalizados Registrados (`.bob/custom_modes.yaml`)

Solo `evidence-auditor` se invoca desde el código (`backend/app/pipeline/evidence_audit.py`); el resto está definido pero **no conectado a ningún flujo**.

| Slug | Nombre | Permisos | Objetivo | Conectado al pipeline |
|---|---|---|---|---|
| `evidence-auditor` | Evidence Auditor | `read` | Inspección forense con evidencia de archivo y línea (schema v1). | Sí |
| `migration-architect` | Migration Architect | `read` | Selección del primer corte y 3 opciones de migración Strangler Fig. | No |
| `contract-keeper` | Contract Keeper | `read, edit` | Creación de pruebas de caracterización golden-master con pytest. | No |
| `strangler-surgeon` | Strangler Surgeon | `read, edit, command` | Implementación del nuevo corte moderno bajo `modern/` detrás de fachada. | No |
| `board-narrator` | Board Narrator | `read` | Redacción del memo ejecutivo para la junta sin inventar cifras. | No |
| `polyglot-architect` | Polyglot Architect | `read` | Mapeo de tipos y patrones cruzados (FastAPI ↔ NestJS ↔ Spring Boot). | No |
| `blast-radius-guard` | Blast Radius Guard | `read` | Simulación estática pre-PR de radio de explosión y fallas en cascada. | No |
| `code-skeptic` | Code Skeptic | `read` | Tribunal adversarial para estresar y validar propuestas técnicas. | No |
| `git-archaeologist` | Git Archaeologist | `read, command` | Minería forense de repositorios git con PyDriller. | No |

## Invocación desde Python

`BobAdapter.run` (`backend/app/adapters/bob_adapter.py`) ejecuta `bob run --format json --mode <modo> --workspace <ruta> --max-turns N --max-cost N --trust`
con una **lista de argumentos, sin `shell=True`**, y entrega el prompt por **stdin**; el texto del repositorio nunca entra en la línea de comandos.

## Patrones de orquestación (diseño, no ejecutados)

Ninguno de estos flujos está implementado ni medido. Se conservan como propuesta.

- **Tribunal adversarial** (`migration-architect` propone, `code-skeptic` objeta, veredicto en 4 rondas).
- **Puerta shift-left pre-PR** (`blast-radius-guard` con un puntaje compuesto de radio de explosión). El puntaje CBRS que aparecía aquí no existe en el producto: el riesgo real es `risk_matrix` (`backend/app/pipeline/decision_metrics.py`).

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
python -m app.pipeline.run_audit ../samples/facturaya-v1          # live
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

### Actividad en vivo y rescate de sesiones (verificado en Bob Shell 2.0.5)

- `bob run --format stream-json` emite por stdout `message` (texto del asistente en fragmentos), `tool_use`,
  `tool_result` y `result`. El `result` no trae `last_message`: el mensaje final se reconstruye con el texto
  posterior a la última herramienta (`BobAdapter.run_stream`).
- `tool_use` y `tool_result` llegan **al terminar** la herramienta: las llamadas paralelas a `spawn_subagent`
  aparecen juntas cuando todos los subagentes acabaron.
- `cost`, `subagent_start` y `subagent_end` (con herramientas, turnos, duración y coste de cada subagente)
  **solo van al log** `~/.bob/logs/shell/bob-shell-*.log`. `BobLogTail` sigue el log de la sesión (el que
  menciona su workspace) para mostrarlos en tiempo real.
- `bob run --resume <task_id>` repite primero el historial (desde el prompt original) y después procesa el
  prompt nuevo; `--max-cost` es acumulado para toda la sesión.
- Las sesiones se guardan en `~/.bob/db/bob.db` (tabla `tasks`, `env.workspace`): si el stream se corta
  antes del `result`, `BobAdapter.find_session_id` localiza la sesión para reanudarla.
- El pipeline reserva el 20 % (máx. 1 bobcoin) de `BOB_MAX_COST` para cerrar la sesión: si Bob agota la
  exploración o se corta la conexión sin JSON, la reanuda con un turno que solo pide el resultado. El coste
  total nunca supera `BOB_MAX_COST`.
- La actividad de cada etapa queda en `artifacts/jobs/<id>/events.jsonl` y se sirve con
  `GET /api/audits/{id}/events?after=N`. La vitrina reproduce `contracts/fixtures/bob-events-facturaya.jsonl`.
- Al apagarse, el servidor termina las sesiones de Bob en curso (`terminate_active_sessions`): un reinicio
  no deja procesos gastando bobcoins.
