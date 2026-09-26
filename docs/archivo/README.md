# Archivo: material previo que no forma parte del producto

Esta carpeta conserva, por transparencia, material de diseño y planificación que se produjo durante el
hackatón pero que **no describe lo que hace CodeArchaeologist hoy**. Nada del producto lo importa ni lo usa.
Se movió aquí para que el repositorio de entrega no presente como funciones cosas que no están implementadas.

| Archivo | Qué es | Por qué está archivado |
|---|---|---|
| `agent.yaml` | Manifiesto de un experimento con un catálogo de agentes y skills. | No lo carga Bob ni el backend. Menciona modelos y "pilares" que no forman parte del producto. |
| `contexts/` | Contextos de los pilares propuestos (tribunal adversarial, simulación de riesgo, migración políglota…). | Esos pilares se descartaron (ver `docs/decisions.md`); no hay código que los use. |
| `bob-session-report.md` | Reporte técnico de la primera integración con Bob. | Describe como implementados pilares que se descartaron (CBRS, FastMCP, PyDriller, tribunal). El registro vigente y respaldado es `docs/bob-usage.md`. |
| `planificacion/tasks.md` y `create_issues.sh` | Plan de tareas por hora del evento y el script que creaba issues desde él. | Planificación interna, ya ejecutada. |
| `planificacion/plan-correcciones-26-09.md` | Plan de correcciones del 26 de septiembre. | Planificación interna, ya ejecutada. |

Lo que sí describe el producto está en el [README](../../README.md), en [docs/motor-de-migracion.md](../motor-de-migracion.md)
y en [docs/bob-usage.md](../bob-usage.md).
