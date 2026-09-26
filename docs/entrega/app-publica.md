# Publicar la app para el jurado

Cómo dejar la URL pública lista para lablab.ai sin exponer credenciales ni quedarse sin bobcoins a mitad
del juzgamiento.

## 1. Qué ve cada visitante

| Camino | ¿Pide token? | ¿Gasta bobcoins? | Para quién |
|---|---|---|---|
| Inicio → **FacturaYa · ya generado** → **Abrir el análisis de FacturaYa** (vitrina importada) | No | No | Cualquiera: jurado, público. Es el camino principal. |
| Recorrer la vitrina: resumen, sesión de Bob, riesgos, arquitectura, recomendación de migración, primer corte probado, memo DOCX | No | No | Cualquiera |
| Inicio → **Subir ZIP** → **Auditoría con evidencia** | Sí | Hasta ~4 por auditoría | Jurado con token |
| Inicio → **Subir ZIP** → **Solo modernización** | Sí | No al subir; sí al usar el Estudio | Jurado con token |
| Preguntarle a Bob sobre un análisis | Sí | Hasta 0,8 por pregunta | Jurado con token |
| Estudio de modernización (evaluar, planear, implementar) | Sí | Hasta ~9 por recorrido completo | Jurado con token |

La vitrina reproduce una sesión real de Bob grabada el 26 de septiembre (12 hallazgos, 14/14 evidencias,
1,15 bobcoins cuando se grabó) y la muestra con la etiqueta `imported`. Todo lo que el jurado necesita para
evaluar el producto funciona **sin token y sin gasto**.

## 2. API key de Bob

- **De quién:** del integrante con más bobcoins disponibles en su presupuesto mensual (en la última revisión,
  la cuenta de Jean tenía 40 de presupuesto y 1,14 usados). Revisarlo con `bob` → resumen de tarea
  (*Monthly Budget* / *Monthly Usage*) justo antes de enviar.
- **Dónde:** solo en Render → *Environment* → `BOB_API_KEY`. Nunca en el repo, en el video, en capturas
  ni en el formulario de lablab.ai.
- **El presupuesto mensual de esa cuenta es el tope global:** si se agota, lo live deja de funcionar, pero la
  vitrina sigue en pie porque no llama a Bob.
- **Cuándo cambiarla:** si la cuenta baja de ~10 bobcoins durante el juzgamiento, pegar la key de otro
  integrante en Render (se redepliega solo, en ~1 minuto, sin tocar el código).

## 3. Token de acceso (`LIVE_AUDIT_TOKEN`)

**Recomendación: mantenerlo obligatorio y no publicarlo.** Las páginas de proyecto de lablab.ai son
públicas: un token escrito ahí lo puede usar cualquiera para gastar el presupuesto.

Opciones, de más a menos segura:

1. **Token bajo pedido (recomendada).** En la descripción del proyecto se escribe:
   *"El análisis real de FacturaYa funciona sin credenciales (Inicio → FacturaYa · ya generado). Para
   auditar su propio repositorio con Bob en vivo, pida un token de acceso a <correo del equipo>."* Se entrega
   por mensaje privado.
2. **Token dedicado al jurado.** Si lablab.ai ofrece un campo privado para jueces, generar un token nuevo
   solo para el juzgamiento, pegarlo en Render y escribirlo en ese campo. Al terminar el juzgamiento, cambiar
   el valor en Render (rotarlo).
3. **Token público (no recomendada).** Solo si las bases lo exigen. En ese caso, dejar los topes de la
   sección 4, vigilar el gasto y rotar el token al cerrar el juzgamiento.

Generar un token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`. En Render también se
puede regenerar desde *Environment*. Nunca reutilizar el token del equipo para el jurado.

## 4. Límites de bobcoins: no quitarlos

Quitar los topes no hace la app más convincente y sí permite que una sola sesión se coma el presupuesto
(ya pasó: un ZIP grande gastó 5 bobcoins sin terminar). `render.yaml` deja estos valores:

| Variable | Valor en Render | Qué limita |
|---|---|---|
| `BOB_MAX_COST` | 3 | Bobcoins por auditoría, incluido el turno de rescate |
| `BOB_MAX_TURNS` | 30 | Turnos del orquestador |
| `BOB_TIMEOUT_S` | 600 | Segundos por sesión |
| `MODERNIZE_PLAN_MAX_COST` | 1.5 | Evaluación y plan del Estudio |
| `MODERNIZE_STEP_MAX_COST` | 2 | Cada paso implementado |
| `MODERNIZE_TOTAL_MAX_COST` | 4 | Una implementación completa |
| `MODERNIZE_MAX_STEPS` | 5 | Pasos por implementación |

Fijos en el código: `migration-architect` (1 bobcoin, 6 turnos) y el chat (0,8 bobcoins, 12 turnos). El
servidor además solo corre **una** auditoría live a la vez.

**Peor caso por acción:** auditoría live ≈ 4 bobcoins (3 + 1 del arquitecto); pregunta ≈ 0,8; Estudio
completo ≈ 9 (1,5 + 1,5 + hasta 6 en la implementación). Con 40 bobcoins alcanza para varias pruebas del
jurado, pero no para un uso abierto: por eso el token.

Las corridas reales costaron bastante menos que el tope: entre 0,57 y 1,44 bobcoins por auditoría de
FacturaYa y entre 0,14 y 0,36 por pregunta o paso (ver `docs/bob-usage.md`).

## 5. Variables en Render (resumen)

| Variable | Valor |
|---|---|
| `BOB_API_KEY` | Key del integrante con más presupuesto (a mano, `sync: false`) |
| `LIVE_AUDIT_TOKEN` | Aleatorio; se comparte por canal privado |
| `BOB_ACCEPT_LICENSE` | `true` |
| `ENABLE_DEV_CORS` | `false` |
| Topes de la sección 4 | Los de `render.yaml` |
| `ALLOW_NON_LIVE_MODES` | **No definirla** (deja el modo `example` apagado en producción) |

## 6. Plan free de Render

- **Se duerme tras 15 minutos sin tráfico**: la primera visita tarda ~1 minuto. Durante el juzgamiento,
  configurar un monitor gratuito (p. ej. UptimeRobot) que haga `GET /health` cada 10 minutos, o subir al plan
  Starter mientras dure la evaluación.
- **Disco efímero**: cada redeploy borra los análisis live. La vitrina se regenera sola al abrirla.
- **512 MB de RAM**: la vitrina va sobrada. Si una auditoría live falla por memoria, la vitrina sigue
  funcionando; la alternativa es el plan Starter.
- **No fusionar a `main` durante el juzgamiento** salvo arreglos urgentes: cada merge redepliega y deja la
  URL caída unos minutos.
- **Inicio abre en la vitrina:** la pestaña por defecto es "FacturaYa · ya generado", que no pide token ni
  gasta bobcoins. "Subir ZIP" sigue a un clic y pide token (`frontend/src/views/ProjectsView.tsx`).

## 7. Prueba de humo antes de enviar

Desde una ventana de incógnito, con la URL pública:

- [ ] `GET /health` responde `{"status":"ok"}`.
- [ ] `GET /api/bob/status` muestra `installed`, `api_key_configured` y `live_requires_token` en `true`.
- [ ] **FacturaYa · ya generado → Abrir el análisis de FacturaYa** abre el análisis con la etiqueta `imported`.
- [ ] Se ven la sesión de Bob, los 12 hallazgos con su código citado, la recomendación de migración
      (`GET /invoices`) y el primer corte con 6/6 pruebas.
- [ ] El memo DOCX se descarga y abre.
- [ ] Sin token, subir un ZIP y preguntarle a Bob piden el token y no arrancan.
- [ ] Con el token, una pregunta corta a Bob responde (gasta < 1 bobcoin).
- [ ] El formulario de lablab.ai tiene la URL, el enlace al repo y la nota de cómo pedir el token; el token
      en sí **no** aparece.
- [ ] Ninguna captura, video o texto de la entrega muestra la API key ni el token.
