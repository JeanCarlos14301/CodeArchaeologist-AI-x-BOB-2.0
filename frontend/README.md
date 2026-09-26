# Frontend

Vite + React 19 + TypeScript + Tailwind 4. El build (`dist/`) lo sirve FastAPI como estáticos.

- **Dueño:** Edgar (E-01 a E-08). Esta es una versión básica para ver el pipeline funcionando.

## Uso

```bash
npm install
npm run dev     # http://localhost:5173, con proxy de /api y /health a http://127.0.0.1:8000
npm run build   # genera dist/, que FastAPI sirve en http://127.0.0.1:8000
```

## Qué muestra
- Estado de IBM Bob: instalación, API key, modos, subagentes y skills cargados desde `.bob/`.
- Abrir la auditoría real grabada de `facturaya-v1` en modo `imported`, sin token ni bobcoins.
- Subir un ZIP y lanzar una auditoría `live` con token.
- Línea de tiempo del job (sandbox → evidence-auditor → validador → primer corte → expediente).
- Hallazgos por severidad; cada evidencia abre el código citado con las líneas resaltadas.
- Hallazgos rechazados por el validador (evidencia que no coincide con el código).

Tipos en `src/types.ts`, espejo de `backend/app/contracts/schema_v1.py`.

## Modos visibles y privacidad
La vitrina usa una respuesta real versionada y queda marcada como `imported`. El flujo live es: ZIP + token ->
`POST /api/audits/upload` -> extracción segura -> Bob real (`evidence-auditor`) -> validación determinista -> expediente.
- **Token:** cabecera `X-Live-Token` = `LIVE_AUDIT_TOKEN`. Sin esa variable el servidor rechaza cargas (503).
- **Lecturas privadas:** el frontend conserva el token en memoria y lo envía al leer el expediente, fuente, grafo, arquitectura,
  migración y descargas de un ZIP. Sin token, las subidas no aparecen en el historial y las rutas responden 403.
- **Mapa neuronal** (`/api/audits/{id}/graph`): funciones y llamadas medidas con AST; marca la función que contiene cada evidencia y
  sus llamadores (impacto). Se enciende según la etapa (3 valida, 4 expediente).
- **Arquitectura** (`/api/audits/{id}/architecture`): módulos, dependencias, rutas, complejidad y SQL medidos sobre el código.
- **Migración:** para FacturaYa muestra legado y FastAPI lado a lado con los casos pytest reales. Para un ZIP se informa
  `not_run`, porque el producto nunca ejecuta código subido por usuarios.
- **Descargas:** `dossier.json`, `bob-result.json`, `board_memo.docx` y, cuando corresponde, `migration.diff`.
