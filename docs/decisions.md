# Decisiones

| ID | Decisión |
|----|----------|
| D1 | El valor es expediente validado + primer corte probado, no un informe libre. |
| D2 | Somos la capa de decisión previa; complementamos los paquetes de modernización de IBM, no competimos. |
| D3 | Primer corte = mejor relación valor/riesgo: `GET /invoices/{id}`. |
| D4 | Migración P0 sobre el repo demo; P1 sobre ZIP arbitrarios. |
| D5 | DOCX es P0; PPTX de 6 diapositivas es P1, desde el mismo JSON. |
| D6 | Orquestador determinista en Python; Bob en modos acotados con subagentes. |
| D7 | Ninguna cifra sin medición; riesgo = impacto × incertidumbre con criterios. |
| D8 | Modo de ejecución siempre visible: `live`, `imported`, `example`. |
| D9 | Repos de muestra preparados antes y declarados; producto desde el kickoff. |
| D10 | Solo Python 3 + Flask + SQLite para el MVP P0 inicial; arquitectura ampliada a políglota para P1. |
| D11 | Un contenedor: FastAPI sirve API y build de React. Plan B: túnel. |
| D12 | Si Bob no corre en servidor: modo asistido importando JSON. |
| D13 | **Reemplazada por el Estudio de modernización** (D37): la persona elige destinos como NestJS, Spring Boot o Express y Bob implementa el plan sobre una copia; no hay matrices de traducción de conceptos. Propuesta original: Extensibilidad políglota: soporte de migraciones cruzadas (FastAPI → NestJS, Express, Spring Boot) usando matrices de traducción de conceptos y contratos de caracterización. |
| D14 | **Descartada, no implementada** (ver D38). Propuesta original: Shift-Left Risk Gating: simulador de radio de explosión (`blast-radius-simulator`) previo a PR, analizando grafos de llamadas transitivos y mutaciones de BD sin mutar código. |
| D15 | **Descartada, no implementada** (ver D38). Propuesta original: Tribunal adversarial multi-agente: dialéctica formal Arquitecto vs. Escéptico (`code-skeptic`) para desafiar suposiciones, condiciones de carrera y deuda oculta. |
| D16 | **Descartada, no implementada** (ver D38). Propuesta original: Minería forense de git y AST: integración de PyDriller (hotspots de churn vs. bugs) y Tree-sitter/AST para cartografía estructural y diagramas ER en Mermaid. |
| D17 | **Descartada, no implementada** (ver D38). Propuesta original: Inyección de telemetría externa FastMCP: conector a DuckDB, SQLite en modo lectura y GitHub para enriquecer hallazgos estáticos con métricas de tráfico y fallos en producción. |
| D18 | Adoptado el [template oficial IBM Hackathon](https://github.com/watsonxhackathon/ibm-hackathon-template): `.bobignore`, patrones de seguridad de `.gitignore` y `SECURITY.md` no se modifican ni se eliminan. |
| D19 | Ajuste de reglas (2026-09-25): video de envío ≤ 3:00 (antes ≤ 4:00), con ≥ 90 s de demo en vivo obligatoria; ver `docs/entrega/guion-video.md`. |
| D20 | Ajuste de reglas (2026-09-25): el repo debe incluir capturas del resumen de sesión de Bob de cada integrante, en `bob-sessions/<persona>/`; ver `SECURITY.md` sobre cómo tomarlas sin exponer credenciales. |
| D21 | Ajuste de reglas (2026-09-25): el formulario de envío añade "Long Description" e "IBM Bob Usage Statement", ambos con tope de 500 palabras; ver `docs/entrega/README.md`. |
| D22 | Las auditorías originadas en ZIP son privadas: listado y toda lectura derivada exigen `X-Live-Token`; las muestras registradas permanecen públicas. |
| D23 | La vitrina pública usa la grabación versionada de FacturaYa de las 13:50. La corrida de las 15:22 no se anuncia como reproducible porque sus artefactos no están en el repositorio. |
| D24 | El memorando se genera primero con narrativa basada solo en datos. Una narrativa de `board-narrator` solo podrá entrar cuando un validador rechace cualquier cifra ausente del JSON. |
| D25 | Riesgo = peso de severidad × (1 + llamadores transitivos). PERT depende de rutas, funciones, líneas citadas y complejidad afectada, con fórmula y supuestos visibles. |
| D26 | El primer corte es implementación de referencia del equipo y se ejecuta solo sobre muestras registradas. Para ZIP de usuarios se informa `not_run`; nunca se ejecuta su código. |
| D27 | La API pública es `/api/audits`; el motor histórico `/api/jobs` permanece apagado y no se documenta como capacidad entregada. |
| D28 | Todo lo que se publica sobre un análisis (feed de actividad, error del job) se trata como público: las rutas absolutas del servidor se reducen a su nombre final y los fallos de Bob llegan con un motivo genérico y accionable; stderr y el detalle quedan solo en el log del servidor. |
| D29 | El registro de actividad tiene tope (5 000 eventos por análisis; por encima solo se escriben los eventos de etapa y cierre) y el arranque de auditorías live es atómico (comprobar y crear bajo un candado): nunca dos sesiones de Bob a la vez. |
| D30 | El ranking de rutas y roadmap por olas es determinista: score = (valor × facilidad) / riesgo (ampliado en D34); PERT por ola y corte con aviso heurístico explícito ("Estimación heurística, no calibrada"); el motor legado /api/jobs se elimina por completo. Ver `docs/motor-de-migracion.md`. |
| D31 | Cada sesión de Bob queda aislada de forma determinista (`backend/app/adapters/bob_workspace.py`): los modos que editan llevan en `fileRegex` el marcador `__WORK_ROOT__`, que falla cerrado hasta sustituirse por la ruta absoluta del workspace (Bob compara con rutas absolutas) y rechaza segmentos `..`; a los workspaces solo viajan subagentes de solo lectura; el proceso de Bob no recibe los secretos de la app (solo `BOB_*`). |
| D32 | Las respuestas del servidor llevan CSP (`script-src 'self'`, sin `unsafe-eval`), `X-Frame-Options: DENY`, `nosniff` y `Referrer-Policy: no-referrer`. Las subidas para «solo modernización» (`modernize:`) son tan privadas como las de auditoría: no aparecen en el listado público. |
| D33 | Mientras Bob trabaja, la interfaz muestra lo que hace de verdad (lecturas, búsquedas, skills, subagentes) desde su stream: en la consola del análisis, en el Estudio y en el chat (`GET /api/audits/{id}/ask/{request_id}/progress`). Nunca progreso simulado. |
| D34 | El puntaje de ruta incluye un factor de datos de negocio: `valor × facilidad × datos / riesgo`, con `datos = 1` si el alcance lee o escribe alguna tabla y `0,5` si no. Aplica D3 (primer corte visible para negocio): sin él, `POST /logout` quedaba primera por contener la línea de evidencia del CSRF. En la vitrina, el motor recomienda `GET /invoices`; el corte de referencia ejecutado sigue siendo `GET /invoices/{id}` (D3, D26) y la interfaz y el memo muestran la diferencia. |
| D35 | `migration-architect` redacta solo la lectura cualitativa de los 3 mejores candidatos del ranking. Un validador en código exige un endpoint del ranking por opción, hallazgos que ese candidato mitiga, cero cifras y que la opción recomendada sea la del motor; si falla, no hay opciones (nunca plantillas). Tope: 6 turnos, 1 bobcoin, sin subagentes. |
| D36 | La vitrina importada se reutiliza: abrirla varias veces devuelve el mismo análisis mientras no haya fallado. Evita que visitas repetidas llenen el disco o la CPU del servidor público. |
| D37 | El Estudio de modernización tiene tope por implementación además del tope por paso: `MODERNIZE_MAX_STEPS` (8 por defecto) y `MODERNIZE_TOTAL_MAX_COST` (6 bobcoins por defecto). Los pasos que no caben quedan `skipped` con el motivo. |
| D38 | Material previo que no describe el producto (manifiesto `agent.yaml`, contextos de pilares descartados, planes por hora, reporte de la primera integración) se archiva en `docs/archivo/` en lugar de borrarse. |
| D39 | Documentación de entrega primero en español (`docs/entrega/`); la copia en inglés para el formulario de lablab.ai se hace al final, a partir de esos textos. |

## Respuestas del kickoff (J-01)
1. **Alcance técnico**: El núcleo arranca con Flask + SQLite a FastAPI, extensible inmediatamente a NestJS y microservicios mediante el catálogo de agentes especializados.
2. **Seguridad de ejecución**: Código analizado es 100% data, nunca instrucciones (Prompt Defense Baseline activo en todos los agentes).
3. **Métricas de riesgo**: Calculadas por código determinista en Python / AST, nunca inventadas por el modelo de lenguaje.
