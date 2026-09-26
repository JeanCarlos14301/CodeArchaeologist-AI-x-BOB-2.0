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

## Cómo tomar la captura (2 minutos)

1. Desde la raíz del repo, con la cuenta propia de Bob:
   ```bash
   bob run --mode evidence-auditor --max-turns 3 --max-cost 0.3 --trust "Sin modificar archivos: lista los archivos .py de samples/facturaya-v1 y explica qué hace app.py"
   ```
   Cuesta menos de 0,3 bobcoins. También sirve una sesión interactiva de `bob`: al cerrarla muestra el
   resumen.
2. Capturar la terminal donde se vean el comando, la respuesta y el bloque **Task Summary** (costo, duración,
   Task ID).
3. Guardarla como `bob-sessions/<integrante>/AAAA-MM-DD_<tarea>.png` (p. ej. `2026-09-26_E-09.png`).
4. Registrar la sesión en `docs/bob-usage.md` (fecha, integrante, modo, tarea, resultado, respaldo).

## Antes de hacer commit de una captura

Según [SECURITY.md](../SECURITY.md): recortar o difuminar todo lo que no sea el resumen de la sesión. En
particular, **ninguna API key, token ni credencial visible** (tampoco el campo de token de la app ni el
dashboard de Render). `.bobignore` evita que Bob *registre* credenciales, pero una captura puede mostrar una
en pantalla: esa revisión es manual. Un correo electrónico visible no es una credencial, pero se puede
difuminar si el integrante lo prefiere.

El registro completo de sesiones está en [docs/bob-usage.md](../docs/bob-usage.md).
