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

## Motores del backend y mapa neuronal
- Al arrancar detecta `GET /api/jobs` (motor de 11 etapas de Daniel). Si responde, usa ese motor: demo, holdout y ZIP reales,
  línea de tiempo con las etapas y mensajes del pipeline, expediente `DossierResult`, arquitectura/PERT, migración, pruebas y descargas.
- Si `/api/jobs` está apagado (`ENABLE_JOBS_API=false`, despliegue público) cae al motor `/api/audits`; sin backend, modo demostración con fixtures.
- **Mapa neuronal** (`/api/jobs/{id}/graph`, `backend/app/api/graph.py`): funciones reales (AST) y sus llamadas, con las marcas de
  hallazgos, radio de explosión y corte de migración. Las capas se encienden según la etapa (3 valida, 5 radio, 8 corte).
- `/api/jobs/{id}/source` sirve fragmentos del sandbox para el visor de evidencia.
