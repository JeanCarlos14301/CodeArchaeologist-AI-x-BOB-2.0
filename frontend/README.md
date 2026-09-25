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
