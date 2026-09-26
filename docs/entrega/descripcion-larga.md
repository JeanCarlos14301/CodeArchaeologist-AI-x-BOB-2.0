# Long Description (borrador en español)

Campo del formulario de lablab.ai. Tope: 500 palabras. Se traduce al inglés al final (D39).
Solo el texto bajo la línea va al formulario.

---

Toda empresa madura tiene un sistema que nadie se atreve a tocar. Sostiene el negocio, pero su autor ya no
está, no tiene pruebas y cada cambio es una apuesta. Cuando la junta pregunta
"¿cuánto cuesta modernizarlo y por dónde empezamos?", la respuesta suele ser una consultoría de semanas o una
opinión sin respaldo.

CodeArchaeologist responde esa pregunta en minutos y con evidencia. Recibe un repositorio heredado (Python 3,
Flask y SQLite en esta versión) y entrega tres cosas:

1. **Un expediente técnico verificable.** IBM Bob audita el código en modo de solo lectura y delega en
   subagentes especializados (SQL, rutas, seguridad, dependencias). Cada hallazgo cita archivo, líneas y
   fragmento. Un validador en Python comprueba que esa cita exista literalmente en el código; si no calza, el
   hallazgo se rechaza. Nada llega al expediente sin prueba.
2. **Una recomendación de migración que se puede auditar.** Un motor determinista recorre el grafo de
   llamadas, las consultas SQL y la complejidad de cada ruta, y calcula qué migrar primero con una fórmula
   visible: valor × facilidad de prueba × datos de negocio / riesgo. Propone el primer corte, las
   alternativas, la ruta que no conviene tocar primero y una hoja de ruta en tres olas con esfuerzo PERT.
   Los números los calcula el código, no la IA.
3. **Un memo DOCX para la junta directiva** con la decisión, la matriz de riesgo, la recomendación y la
   trazabilidad de cada cifra hasta el código.

Para la muestra controlada FacturaYa, además, se ejecuta un primer corte Strangler Fig: la ruta legada y su
reemplazo moderno pasan la misma batería de pruebas de caracterización (6 de 6). El código subido por
usuarios nunca se ejecuta: se analiza de forma estática.

En el Estudio de modernización, Bob propone un plan por pasos y lo implementa sobre una copia del proyecto,
con topes de gasto.

**Para quién.** Directores de tecnología y equipos de arquitectura que heredan sistemas críticos; consultoras
que necesitan un diagnóstico defendible antes de cotizar; juntas directivas que deben aprobar presupuesto de
modernización sin leer código.

**Qué lo diferencia.**

- *Evidencia antes que narrativa.* Cada afirmación se puede abrir en el código citado. En la vitrina pública,
  14 de 14 citas pasan el validador.
- *La IA propone, el código decide.* Bob encuentra y explica; el riesgo, el orden de migración y el esfuerzo
  salen de cálculos reproducibles. Si Bob contradice al motor o inventa una cifra, su respuesta se descarta.
- *Transparencia de ejecución.* Cada resultado indica si es `live` o `imported`, y la interfaz muestra en
  tiempo real lo que Bob lee, busca y delega.
- *Seguro por diseño.* El repositorio analizado es dato, nunca instrucción; los análisis subidos son privados.

La demo pública abre sin credenciales una auditoría real de IBM Bob sobre FacturaYa: 12 hallazgos validados,
recomendación de migración, primer corte probado y memo descargable.

CodeArchaeologist no reemplaza al equipo que moderniza: le da el mapa, el orden y la prueba para empezar el
lunes.
