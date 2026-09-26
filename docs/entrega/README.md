# Entrega del IBM Bob 2.0 Hackathon

Todo lo que pide lablab.ai, con su estado y dónde está. **Cierre: domingo 27 de septiembre de 2026,
11:00 a. m. ET (10:00 a. m. en Colombia).** Los textos están en español; la copia en inglés se hace al final
(D39).

## Documentos de esta carpeta

| Archivo | Para qué |
|---|---|
| [formulario-lablab.md](formulario-lablab.md) | Cada campo del formulario con su valor y estado |
| [descripcion-larga.md](descripcion-larga.md) | *Long Description* (≤ 500 palabras) |
| [declaracion-uso-bob.md](declaracion-uso-bob.md) | *IBM Bob Usage Statement* (≤ 500 palabras) |
| [guion-video.md](guion-video.md) | Guion del video de 3:00 con 130 s de demo |
| [presentacion.md](presentacion.md) | Esquema de las 9 diapositivas |
| [app-publica.md](app-publica.md) | Cómo publicar la app al jurado: API key, token, topes de bobcoins y prueba de humo |

## Checklist

### Repositorio
- [x] Público, licencia MIT (`LICENSE`), creado desde la [plantilla oficial](https://github.com/watsonxhackathon/ibm-hackathon-template); `.gitignore` y `.bobignore` sin modificar.
- [x] `SECURITY.md` presente; credenciales solo en variables de entorno.
- [x] README en español: problema, solución, uso de Bob, arquitectura, cómo evaluar, seguridad y limitaciones.
- [x] Material previo que no describe el producto, archivado en [docs/archivo/](../archivo/).
- [x] Decisiones al día (`docs/decisions.md`, hasta D39) y registro de Bob (`docs/bob-usage.md`).
- [ ] Revisión final de credenciales: `git log -p | grep -iE "api[_-]?key|token|secret"` sin valores reales; capturas sin datos sensibles.
- [ ] `main` con la versión final (fusionar el PR de esta rama) y rama `develop` eliminada o al día.
- [ ] Copia en inglés de README y documentos de entrega.

### Capturas de sesiones de Bob (una por integrante, como mínimo)
- [x] Felipe: `bob-sessions/felipe/` (terminal con resumen de tarea y sesión live en la app).
- [ ] Jean: hay una captura, pero muestra una tarea con 0 bobcoins. Conviene añadir una de una sesión real (con costo).
- [ ] Daniel: las imágenes actuales muestran ejecuciones de pytest, no el resumen de una sesión de Bob. Falta la captura real.
- [ ] Edgar: carpeta vacía. Falta la captura.

Cómo tomarlas: [bob-sessions/README.md](../../bob-sessions/README.md).

### App pública
- [ ] URL de Render funcionando y pegada en el README y en el formulario.
- [ ] `BOB_API_KEY` del integrante con más presupuesto, cargada en Render.
- [ ] Topes de `render.yaml` aplicados (se sincronizan al fusionar a `main`).
- [ ] Monitor de disponibilidad o plan Starter durante el juzgamiento.
- [ ] Prueba de humo de [app-publica.md](app-publica.md#7-prueba-de-humo-antes-de-enviar) superada desde incógnito.

### Material del formulario
- [x] Título, descripción corta, descripción larga y declaración de uso de Bob (borradores en español).
- [ ] Imagen de portada.
- [ ] Video MP4 ≤ 3:00, con narración y ≥ 90 s de demo.
- [ ] Presentación (PDF).
- [ ] Formulario enviado y verificado desde otra cuenta.

## Criterios del jurado y dónde se demuestran

| Criterio | Dónde se ve |
|---|---|
| Aplicación de la tecnología | Bob en 5 modos del producto, subagentes en paralelo, actividad en vivo, rescate de sesiones (`docs/bob-usage.md`) |
| Presentación | Video, diapositivas y la vitrina pública sin credenciales |
| Valor de negocio | Memo para la junta, recomendación de migración con PERT, primer corte probado |
| Originalidad | La IA propone y el código decide: evidencia validada línea a línea y ranking determinista auditable |
