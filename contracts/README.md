# Contratos

Esquema JSON compartido entre pipeline, Bob, renderizadores y frontend.

- **Dueño:** Daniel (D-01).
- **El contrato v1 se congela en H3.** Cambios posteriores requieren PR revisado por Daniel y aviso al equipo.
- `fixtures/`: ejemplos válidos del contrato (al menos 2, D-01) y la salida real sanitizada de Bob (F-01).

## Contenido
- `schema-v1.json`: generado desde `backend/app/contracts/schema_v1.py` con
  `cd backend && python -m app.contracts.export`. No se edita a mano.
  - `auditor_output`: lo que debe devolver Bob en modo `evidence-auditor`.
  - `dossier`: expediente validado (etapas 2 y 3) con métricas calculadas por código.
- `fixtures/bob-session-facturaya.json`: resultado real de la sesión de Bob que usa la vitrina
  (26-09, `evidence-auditor` con 4 subagentes; modo `imported`).
- `fixtures/bob-events-facturaya.jsonl`: actividad de esa misma sesión (stream-json de Bob + eventos de su
  log: plan, herramientas, subagentes, turnos), sin el contenido de los archivos leídos. La vitrina la
  reproduce con su ritmo original.
- `fixtures/bob-evidence-auditor-facturaya.json`: sesión del 25-09 (6/6 hallazgos esperados). Se conserva
  para la evaluación y las pruebas; reimportable con `--import`.
- `fixtures/dossier-example.json`: expediente de ejemplo (`execution_mode: example`) para el frontend.
