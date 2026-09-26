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
- Lanzar una auditoría de `facturaya-v1` en modo `live`, `imported` o `example`.
- Línea de tiempo del job (sandbox → evidence-auditor → validador → expediente).
- Hallazgos por severidad; cada evidencia abre el código citado con las líneas resaltadas.
- Hallazgos rechazados por el validador (evidencia que no coincide con el código).

Tipos en `src/types.ts`, espejo de `backend/app/contracts/schema_v1.py`.

## Solo datos reales
La app no trae fixtures ni modo ejemplo. Flujo: subir un ZIP + token (siempre obligatorio) -> `POST /api/audits/upload` ->
extracción segura -> Bob real (`evidence-auditor`) -> validación determinista de evidencia -> expediente.
- **Token:** cabecera `X-Live-Token` = `LIVE_AUDIT_TOKEN`. Sin esa variable el servidor rechaza cargas (503).
- **Mapa neuronal** (`/api/audits/{id}/graph`): funciones y llamadas medidas con AST; marca la función que contiene cada evidencia y
  sus llamadores (impacto). Se enciende según la etapa (3 valida, 4 expediente).
- **Arquitectura** (`/api/audits/{id}/architecture`): módulos, dependencias, rutas, complejidad y SQL medidos sobre el código.
- **Descargas:** `dossier.json` y `bob-result.json` reales.
- Migración Strangler Fig, plan PERT y memo DOCX no se muestran: el pipeline de `/api/jobs` los genera con plantillas fijas para
  FacturaYa, no con Bob. Volverán cuando existan con datos reales.
