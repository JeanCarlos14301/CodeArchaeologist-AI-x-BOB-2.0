# Formulario de envío en lablab.ai

Campo por campo, en el orden del formulario. Textos en español por ahora; se traducen al inglés antes de
enviar (D39). **Cierre: domingo 27 de septiembre de 2026, 11:00 a. m. ET (10:00 a. m. en Colombia).**

| Campo | Valor | Estado |
|---|---|---|
| **Project Title** | CodeArchaeologist | Listo |
| **Short Description** | Ver abajo | Listo (traducir) |
| **Long Description** (≤ 500 palabras) | [descripcion-larga.md](descripcion-larga.md) | Listo (traducir y recontar) |
| **IBM Bob Usage Statement** (≤ 500 palabras) | [declaracion-uso-bob.md](declaracion-uso-bob.md) | Listo (traducir; revisar la frase de capturas) |
| **Technology & Category Tags** | Ver abajo | Elegir de la lista del formulario |
| **Cover Image** | Pendiente | Falta: 16:9, nombre + una captura de la app, sin datos sensibles |
| **Video Presentation** (MP4, ≤ 3:00) | Pendiente | Falta: ver [guion-video.md](guion-video.md) |
| **Slide Presentation** | Pendiente | Falta: ver [presentacion.md](presentacion.md) |
| **Public GitHub Repository** | https://github.com/JeanCarlos14301/CodeArchaeologist-AI-x-BOB-2.0 | Verificar que sea público y que `main` tenga la versión final |
| **Demo Application Platform** | Render (contenedor Docker) | Listo |
| **Application URL** | `https://<servicio>.onrender.com` | Falta: pegar la URL real (Render → servicio `codearchaeologist`) |
| Capturas de sesiones de Bob | En el repo, `bob-sessions/<integrante>/` | Faltan Daniel y Edgar; ver [bob-sessions/README.md](../../bob-sessions/README.md) |

## Short Description

> Audita sistemas heredados con IBM Bob y entrega evidencia verificable por archivo y línea, qué migrar
> primero según un cálculo auditable, y un memo para la junta directiva.

(172 caracteres. Si el formulario pide menos, usar: *"IBM Bob audita tu sistema heredado; el código decide
qué migrar primero, con evidencia."*)

## Tags sugeridos

- **Tecnología:** IBM Bob, Python, FastAPI, React, TypeScript, Tailwind CSS, SQLite, Docker, Render.
- **Categoría:** Developer Tools, Legacy Modernization, Code Analysis, Enterprise, AI Agents.

Usar los que existan en la lista del formulario; no inventar etiquetas nuevas si no lo permite.

## Nota sobre el acceso en vivo (va en la Long Description o en un campo de notas)

> El análisis real de FacturaYa funciona sin credenciales (Inicio → FacturaYa · ya generado). Para auditar
> su propio repositorio con IBM Bob en vivo, pida un token de acceso a <correo del equipo>.

El token **nunca** se escribe en el formulario. Detalle en [app-publica.md](app-publica.md).
