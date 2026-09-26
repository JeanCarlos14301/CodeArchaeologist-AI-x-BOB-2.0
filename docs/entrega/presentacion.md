# Presentación (esquema de diapositivas)

Entregable obligatorio del formulario ("Slide Presentation"). 9 diapositivas, las mismas que se usan en el
video. Las cifras del producto salen de la vitrina pública; las de mercado **solo con fuente citada** en la
diapositiva (AGENTS.md: no inventar métricas). Donde dice *[cifra con fuente]*, poner el dato y su fuente o
quitar la frase.

| # | Título | Contenido | Visual |
|---|---|---|---|
| 1 | CodeArchaeologist | "Por dónde empezar a modernizar, con evidencia." Construido con IBM Bob 2.0. Logo y nombre del equipo | Portada (misma imagen que la *cover image*) |
| 2 | El problema | Sistemas críticos sin pruebas ni autor; la junta debe aprobar presupuesto sin poder leer código. *[cifra con fuente sobre costo de deuda técnica o de mantener sistemas heredados]* | Un monolito con "no tocar" |
| 3 | La solución | Tres entregables: expediente verificable, recomendación de migración calculada, memo para la junta. Primer corte probado en la muestra controlada | Tres columnas |
| 4 | Cómo funciona | Repositorio → Bob (`evidence-auditor` + 4 subagentes) → validador de evidencia → motor determinista (grafo, SQL, complejidad) → interfaz y memo | Diagrama del README |
| 5 | IBM Bob en el centro | 11 modos, 18 subagentes y 24 skills propios; 5 modos en producción; actividad de Bob en vivo; topes y rescate de sesiones | Captura de la vista "Sesión de Bob" |
| 6 | Evidencia, no opinión | 12 hallazgos validados, 14/14 citas verificadas en la vitrina; cada hallazgo se abre en el código citado | Captura de un hallazgo con su código |
| 7 | Qué migrar primero | Fórmula `valor × facilidad × datos / riesgo`; corte recomendado `GET /invoices`; ruta a evitar `/invoices/new`; 3 olas con PERT; primer corte de referencia 6/6 pruebas | Captura de "Recomendación y primer corte" |
| 8 | Para quién y por qué nosotros | CTOs y arquitectos que heredan sistemas; consultoras antes de cotizar; juntas directivas. Diferencia: la IA propone y el código decide; ejecución transparente (`live` / `imported`); seguro por diseño | Tabla comparativa cualitativa (sin cifras de competidores) |
| 9 | Equipo y siguiente paso | Jean (producto, DevOps, pitch), Felipe (integración de Bob), Daniel (backend y métricas), Edgar (frontend y UX). Siguiente paso: más stacks de entrada. Enlaces a la demo y al repo | Fotos o avatares |

## Formato

- Exportar a PDF para el formulario (y conservar el editable).
- Colores y tipografía de `DESIGN.md` para que coincida con la app.
- No incluir capturas donde se vea un token, una API key o el dashboard de Render.
