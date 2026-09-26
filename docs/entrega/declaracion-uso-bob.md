# IBM Bob Usage Statement (borrador en español)

Campo del formulario de lablab.ai. Tope: 500 palabras. Se traduce al inglés al final (D39).
Solo el texto bajo la línea va al formulario. Cada afirmación está respaldada en `docs/bob-usage.md`.
**Antes de enviar:** la frase sobre `bob-sessions/` solo es cierta cuando estén las capturas de los cuatro
integrantes (ver `bob-sessions/README.md`); si falta alguna, quitarla o corregirla.

---

IBM Bob 2.0 es el motor de análisis de CodeArchaeologist y también fue una herramienta de trabajo del equipo
durante el hackatón.

**Arquitectura.** El backend (FastAPI) invoca Bob Shell 2.0.5 con `bob run` mediante `subprocess`, con una lista
de argumentos y el prompt por stdin: el texto del repositorio analizado nunca entra en la línea de comandos. Cada
sesión corre sobre una copia aislada del repositorio, sin la verdad de referencia de evaluación y sin los
secretos de la aplicación. Leemos el stream de eventos (`--format stream-json`) y el log de Bob para mostrar en
la interfaz, en tiempo real, qué lee, busca y delega.

**Modos, subagentes y skills propios.** Escribimos 11 modos personalizados en `.bob/custom_modes.yaml`, 18
subagentes y 24 skills. El producto usa cinco modos:

- `evidence-auditor` (solo lectura) orquesta la auditoría y delega en paralelo en subagentes especializados:
  `legacy-sql-auditor`, `legacy-route-mapper`, `legacy-security-scanner` y `legacy-dependency-tracer`. Devuelve
  hallazgos en JSON con archivo, líneas y fragmento; un validador en Python rechaza cualquier cita que no exista.
- `migration-architect` redacta la lectura cualitativa de los tres mejores cortes que calcula nuestro motor
  determinista. Si propone otro corte o escribe cifras, su respuesta se descarta.
- `modernization-planner` y `modernization-surgeon` forman el Estudio de modernización: el primero evalúa el
  stack y arma un plan por pasos; el segundo implementa cada paso editando solo una copia del proyecto.
- El modo nativo `ask` responde preguntas del usuario sobre el código analizado.

**Controles.** Cada sesión tiene tope de turnos, tiempo y bobcoins. Si Bob agota su presupuesto o se corta la
conexión antes de entregar el JSON, el pipeline reanuda la misma sesión (`--resume`) con un turno de cierre
reservado dentro del tope. Los números del producto (riesgo, orden de migración, esfuerzo PERT) los calcula
código, nunca Bob.

**Cómo usamos Bob para construir el producto.** Las sesiones quedaron registradas con su ID de tarea y costo:

- Diagnosticamos con `--resume` por qué falló la auditoría de un ZIP grande: sus cuatro subagentes agotaron el
  tope sin entregar resultado. Eso motivó el rescate automático de sesiones.
- Probamos si Bob podía escribir en modo headless y descubrimos que `fileRegex` se compara con la ruta
  absoluta. Con eso diseñamos el aislamiento que usa hoy el Estudio y lo verificamos con Bob: escribió en su
  copia y se le bloquearon tres intentos de salir de ella.
- Exploramos el formato `stream-json` para construir la actividad en vivo, y usamos `ask` para probar la
  interfaz del chat con respuestas largas.
- Grabamos la sesión real que reproduce la vitrina pública: 4 subagentes en paralelo, 12 hallazgos, 14 de 14
  evidencias válidas, 1,15 bobcoins y 165 segundos.

Cada integrante dejó capturas del resumen de sus sesiones de Bob en `bob-sessions/`.

**Honestidad de ejecución.** Cada resultado dice si viene de una sesión `live` o de una sesión real grabada
(`imported`). La demo pública reproduce esa grabación para que cualquiera la vea sin credenciales ni costo; las
auditorías en vivo requieren token.
