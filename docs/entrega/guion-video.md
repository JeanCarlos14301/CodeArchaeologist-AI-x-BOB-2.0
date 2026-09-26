# Guion del video (máximo 3:00, MP4)

Reglas del jurado: nada después de 3:00 cuenta; al menos **90 segundos** de la solución funcionando en
pantalla; narración; demostración clara del uso de IBM Bob. La etiqueta `live` / `imported` debe verse
durante la demo.

**Antes de grabar:** abrir la URL pública 2 minutos antes (Render free se duerme), ventana de incógnito,
zoom del navegador al 110 %, sin pestañas ni barras con datos personales. Nunca mostrar la API key, el
token ni el dashboard de Render.

## Escenas

| Tiempo | Duración | Escena | Qué se ve | Narración (borrador) |
|---|---|---|---|---|
| 0:00–0:20 | 20 s | Problema | Diapositiva 1–2: un monolito de facturación con 10 años, sin pruebas | "Toda empresa tiene un sistema que nadie se atreve a tocar. Cuando la junta pregunta cuánto cuesta modernizarlo y por dónde empezar, nadie tiene una respuesta con evidencia." |
| 0:20–0:30 | 10 s | Solución en una frase | Diapositiva 3: los tres entregables | "CodeArchaeologist usa IBM Bob para auditar el código y entrega un expediente verificable, una recomendación de migración calculada y un memo para la junta." |
| 0:30–0:50 | 20 s | **Demo 1 · Bob trabajando** | Inicio → FacturaYa · ya generado → Abrir el análisis. Vista **Sesión de Bob**: pulsar *Reproducir la sesión*; se ve el plan, las lecturas y la delegación en 4 subagentes | "Esta es una sesión real de Bob sobre FacturaYa. El modo evidence-auditor planifica, lee el código y delega en paralelo en cuatro subagentes: SQL, rutas, seguridad y dependencias." |
| 0:50–1:15 | 25 s | **Demo 2 · Evidencia** | **Riesgos**: abrir F-1 (inyección SQL) y ver el código citado resaltado; mostrar "14/14 citas verificadas" | "Cada hallazgo cita archivo y líneas. Un validador en Python comprueba que la cita exista literalmente en el código. Si no calza, el hallazgo se descarta." |
| 1:15–1:45 | 30 s | **Demo 3 · Qué migrar primero** | **Modernización → Recomendación y primer corte**: corte recomendado `GET /invoices`, fórmula, ruta a evitar `/invoices/new`, olas con PERT | "¿Por dónde empezar? El motor recorre el grafo de llamadas y el SQL y calcula valor por facilidad por datos de negocio sobre riesgo. Recomienda GET /invoices y desaconseja invoices/new: concentra hallazgos, pero escribe en dos tablas. Los números los calcula el código, no la IA." |
| 1:45–2:05 | 20 s | **Demo 4 · Primer corte probado** | Misma vista: legado vs. moderno lado a lado, 6/6 pruebas en verde | "Para la muestra controlada ejecutamos un primer corte Strangler Fig: la ruta legada y su reemplazo moderno pasan las mismas pruebas de caracterización." |
| 2:05–2:25 | 20 s | **Demo 5 · Preguntarle a Bob** | Panel de Bob: preguntar "¿Qué debería migrar primero y por qué?" con token; se ve a Bob leer archivos en vivo | "Y cualquiera con acceso puede preguntarle a Bob sobre el código. Aquí la sesión es live: vemos qué archivos lee antes de responder." |
| 2:25–2:40 | 15 s | **Demo 6 · Memo** | **Reportes**: descargar y abrir el DOCX en la sección "Recomendación de migración" | "Todo termina en un memo para la junta, con la decisión y la trazabilidad de cada cifra hasta el código." |
| 2:40–3:00 | 20 s | Valor y cierre | Diapositivas 8–9: para quién, diferenciación, equipo | "CodeArchaeologist no reemplaza al equipo que moderniza: le da el mapa, el orden y la prueba para empezar el lunes. Construido con IBM Bob 2.0." |

Demo en pantalla: de 0:30 a 2:40 = **130 s** (mínimo exigido: 90 s).

## Notas

- **La demo 5 es la única que gasta bobcoins** (< 1). Si Bob no responde a tiempo al grabar, se puede
  sustituir por el Estudio de modernización o recortar y alargar la demo 3. El resto funciona sin token.
- La vitrina muestra `imported`: decirlo en voz alta ("sesión real grabada"). No presentarla como live.
- No mostrar cifras que la app no muestre. Si se cambia la sesión grabada, revisar las cifras de este guion.
- Exportar MP4 1080p, verificar la duración (≤ 3:00) antes de subir, y subirlo a un enlace público
  (YouTube no listado o el que pida el formulario).
