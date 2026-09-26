# Tareas

Formato: `ID | Dueño | Ventana | Tarea | Aceptación`. Las horas (H0–H48) cuentan desde el kickoff.
`scripts/create_issues.sh` lee esta tabla; si cambias el formato, actualiza el script.

Hitos (se asignan por la hora final de la ventana):
`hito:H3` contrato congelado · `hito:H8` bala trazadora · `hito:H24` MVP · `hito:H32` v1.0 · `hito:H44` envío · `hito:continuo`.

| ID | Dueño | Ventana | Tarea | Aceptación |
|----|-------|---------|-------|------------|
| J-01 | Jean | H0–H1 | Resolver preguntas del kickoff | Respuestas en decisions.md |
| J-02 | Jean | H0–H3 | Dockerfile + FastAPI /health desplegado | URL pública responde |
| J-03 | Jean | H3–H8 | Despliegue automático desde main | Push actualiza URL |
| J-04 | Jean | H4–H10 | 2 cifras de mercado con fuente + slides de negocio | Enlaces |
| J-05 | Jean | H8–H12 | Probar recorrido como jurado | Issues priorizadas |
| J-06 | Jean | H12–H20 | Guion del video | demo-script.md con tiempos |
| J-07 | Jean | H20–H24 | Medición manual vs herramienta | Número con método |
| J-08 | Jean | H24–H30 | Aceptación y tag v1.0 | Recorrido pasa 3 veces |
| J-09 | Jean | H32–H38 | Grabar y editar video | ≤ 3 minutos, ≥ 90 s de demo en vivo |
| J-10 | Jean | H36–H44 | README final y envío | Verificado desde otra cuenta |
| J-11 | Jean | continuo | Captura de resumen de sesión de Bob (cuenta propia) | Imagen en bob-sessions/jean/ |
| F-01 | Felipe | H0–H2 | Bob Shell + JSON real sanitizado | Archivo en contracts/ |
| F-02 | Felipe | H1–H3 | AGENTS.md y 5 modos operativos | bob run --mode responde |
| F-03 | Felipe | H3–H8 | evidence-auditor devuelve esquema v1 | Pasa Pydantic |
| F-04 | Felipe | H8–H14 | migration-architect: 3 opciones y primer corte | Justificado |
| F-05 | Felipe | H12–H18 | contract-keeper: pruebas de caracterización | Pasan en legado |
| F-06 | Felipe | H16–H24 | strangler-surgeon: FastAPI + fachada | Pruebas en verde |
| F-07 | Felipe | H18–H24 | Precisión y recall vs expected-findings | Tabla en evaluation/ |
| F-08 | Felipe | H24–H30 | board-narrator + prueba en holdout | [CANCELADO] La variante era una copia; se retiró. El DOCX activo usa narrativa basada solo en datos. |
| F-09 | Felipe | continuo | bob-usage.md y reporte exportado | Archivo en bob-report/ |
| F-10 | Felipe | H4–H10 | Polyglot Migration: agentes y skill FastAPI→NestJS/Express | Catálogo y matrices completos |
| F-11 | Felipe | H8–H16 | Shift-Left Blast Radius: simulador y puerta pre-PR | [DISEÑO, NO EJECUTADO] No forma parte del producto público. |
| F-12 | Felipe | H12–H20 | Tribunal Adversarial: Arquitecto vs Escéptico | Protocolo 4 rondas con veredicto |
| F-13 | Felipe | H16–H24 | AST Cartographer + PyDriller Git Archaeology | Grafos de llamadas y ER Mermaid |
| F-14 | Felipe | H20–H28 | Telemetría FastMCP: conectores DuckDB / GitHub | Enriquecimiento operativo activo |
| F-15 | Felipe | continuo | Captura de resumen de sesión de Bob (cuenta propia) | Imagen en bob-sessions/felipe/ |
| D-01 | Daniel | H0–H3 | Modelos Pydantic + schema v1 + 2 fixtures | [COMPLETADO] Generado y validado en backend/app/models.py y contracts/ |
| D-02 | Daniel | H2–H6 | API de jobs, SQLite, worker, eventos | [COMPLETADO] Base jobs.db WAL, worker determinista y endpoints REST /api/jobs |
| D-03 | Daniel | H3–H6 | Ingesta segura ZIP + extractores | [COMPLETADO] Anti-ZipSlip, límites 5MB/20MB/300 files y AST/Radon/SQL extractor |
| D-04 | Daniel | H5–H8 | BobAdapter con timeout y modos | [COMPLETADO] Subprocess seguro shell=False y modos live/imported/example |
| D-05 | Daniel | H6–H8 | DOCX mínimo | [COMPLETADO] Renderizado ejecutivo corporativo descargable |
| D-06 | Daniel | H8–H16 | Validador, radio de impacto, riesgo, PERT | [ACTUALIZADO] Riesgo por severidad y llamadores; PERT del primer corte con insumos y supuestos visibles. |
| D-07 | Daniel | H12–H22 | Sandbox pytest + endpoint /migrate | [COMPLETADO] 13 tests legacy PASS, corte FastAPI modern/ y BOLA fixed 404 |
| D-08 | Daniel | H16–H24 | DOCX completo + HTML autónomo | [COMPLETADO] DOCX 7 secciones en Word + HTML con Mermaid interactivo |
| D-09 | Daniel | H24–H30 | PPTX, descarga .diff, manejo de fallos | [COMPLETADO] PPTX 6 diapositivas 16:9 + migration.diff en /api/jobs/{id}/artifacts |
| D-10 | Daniel | continuo | CLI de auditoría, tests y sesión Bob | [COMPLETADO] cli_audit.py funcional de 11 etapas y 14 tests automatizados |
| E-01 | Edgar | H0–H3 | Vite + React + Tailwind | Build servido por FastAPI |
| E-02 | Edgar | H3–H8 | Entrada y línea de tiempo con fixture | Recorrido completo |
| E-03 | Edgar | H6–H8 | Conectar API real | Bala trazadora visible |
| E-04 | Edgar | H8–H16 | Hallazgos y visor de evidencia | Cada hallazgo abre su archivo |
| E-05 | Edgar | H12–H20 | Arquitectura actual vs objetivo | Observado vs inferido |
| E-06 | Edgar | H16–H24 | Split-view + panel de pruebas | Datos reales |
| E-07 | Edgar | H20–H28 | Descargas, modo visible, estados de error | Sin pantallas vacías |
| E-08 | Edgar | H26–H32 | Pulido y capturas | Valor claro en 30 segundos |
| E-09 | Edgar | continuo | Captura de resumen de sesión de Bob (cuenta propia) | Imagen en bob-sessions/edgar/ |
