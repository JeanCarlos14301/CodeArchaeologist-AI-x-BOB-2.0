# Capturas de sesiones de IBM Bob (entregable obligatorio)

Las reglas del hackatón piden que el repositorio público incluya capturas del **resumen de tarea de Bob
(Task Session Summary) de cada integrante**, tomadas desde su propia cuenta. Esta carpeta está versionada y
no aparece en `.gitignore`.

## Estado por integrante

| Integrante | Carpeta | Estado |
|---|---|---|
| Felipe | [felipe/](felipe/) | ✅ `2026-09-26_F-15_bob-run-terminal.png`: `bob run --mode evidence-auditor` con *Task Summary* (0,180 bobcoins, 10,4 s, tarea `39094ee2b09c`). `2026-09-26_F-03_sesion-live-evidence-auditor.png`: la sesión live de la vitrina vista en la app (1,15 bobcoins). |
| Jean | [jean/](jean/) | ⚠️ `EVIDENCE-USEBOB-001.PNG`: *Task Overview* de Bob Shell 2.0.5 (tarea `c54cdc15907f`, 25-09) con 0 bobcoins en esa tarea. Falta una captura de una tarea con costo. |
| Daniel | [daniel/](daniel/) | ❌ Las imágenes actuales muestran ejecuciones de pruebas (pytest y la batería de seguridad), no un resumen de sesión de Bob. Falta la captura. |
| Edgar | [edgar/](edgar/) | ❌ Carpeta vacía. Falta la captura. |

## Qué debe verse en cada captura

Lo que valida el jurado es que **cada integrante usó Bob desde su propia cuenta**. Cada captura debe mostrar:

1. El comando `bob run --mode <modo> …` (o la sesión interactiva) con un **modo de este repo**.
2. La respuesta de Bob sobre código real del proyecto.
3. El bloque **Task Summary** completo: costo en bobcoins **mayor que 0**, duración y Task ID.

Una captura de pytest, del navegador o de una tarea con 0 bobcoins no cuenta como resumen de sesión.

## Qué captura toma cada integrante

Cada uno usa un modo distinto, ligado a su parte del trabajo, para que el conjunto muestre el uso real de los
modos. Todos son de solo lectura y tienen tope de costo. Se ejecutan desde la raíz del repo.

| Integrante | Por qué este modo | Comando |
|---|---|---|
| **Jean** (producto, despliegue, pitch) | El modo que decide qué migrar primero: el corazón del pitch. | `bob run --mode migration-architect --max-turns 6 --max-cost 0.6 --trust "Sin modificar archivos: en samples/facturaya-v1, ¿qué ruta migrarías primero con el patrón Strangler Fig y por qué? Cita archivo y líneas."` |
| **Daniel** (backend y contrato) | Radio de impacto: qué se rompe al tocar la capa de datos. | `bob run --mode blast-radius-guard --max-turns 5 --max-cost 0.5 --trust "Sin modificar archivos: en samples/facturaya-v1, ¿qué rutas y funciones se rompen si cambio db.py? Cita archivo y líneas."` |
| **Edgar** (frontend) | Revisión escéptica del código: cuestiona supuestos antes de migrar. | `bob run --mode code-skeptic --max-turns 4 --max-cost 0.4 --trust "Sin modificar archivos: revisa samples/facturaya-v1/billing.py y señala qué supuestos del cálculo de totales podrían ser falsos. Cita archivo y líneas."` |
| **Felipe** (modos de Bob) | ✅ Ya está (`evidence-auditor`). No hace falta repetir. | — |

Si `bob run` no está disponible, sirve una sesión interactiva: ejecutar `bob`, elegir el modo con `/mode`,
hacer la misma pregunta y cerrar la sesión para que aparezca el resumen.

## Cómo guardarla

1. Capturar la terminal completa (comando, respuesta y Task Summary). Si la respuesta es larga, dos capturas:
   el comando al inicio y el resumen al final.
2. Guardarla como `bob-sessions/<integrante>/AAAA-MM-DD_<modo>.png`, p. ej.
   `bob-sessions/daniel/2026-09-26_blast-radius-guard.png`.
3. Añadir una fila en `docs/bob-usage.md` (fecha, integrante, modo, tarea, costo, Task ID).
4. Actualizar la tabla de estado de arriba.

## Antes de hacer commit de una captura

Según [SECURITY.md](../SECURITY.md): recortar o difuminar todo lo que no sea el resumen de la sesión. En
particular, **ninguna API key, token ni credencial visible** (tampoco el campo de token de la app ni el
dashboard de Render). `.bobignore` evita que Bob *registre* credenciales, pero una captura puede mostrar una
en pantalla: esa revisión es manual. Un correo electrónico visible no es una credencial, pero se puede
difuminar si el integrante lo prefiere.

El registro completo de sesiones está en [docs/bob-usage.md](../docs/bob-usage.md).
