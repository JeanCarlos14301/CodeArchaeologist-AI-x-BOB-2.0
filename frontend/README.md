# Frontend

Workspace de modernización (Vite + React 19 + TypeScript + Tailwind 4), servido por FastAPI desde `dist/`.

- **Diseño:** [../DESIGN.md](../DESIGN.md) (tokens, componentes, reglas). **Producto:** [../PRODUCT.md](../PRODUCT.md).
- **Dueño:** Edgar (E-01 a E-08).

## Uso

```bash
npm install
npm run dev     # http://localhost:5173 con proxy de /api y /health a http://127.0.0.1:8000
npm run build   # genera dist/, que FastAPI sirve en http://127.0.0.1:8000
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `src/styles/tokens.css` | tokens primitivos (`--ca-*`) y semánticos (`@theme`); las paletas por defecto de Tailwind están desactivadas |
| `src/lib/` | estado y dominio sin UI: `workspace.tsx` (proveedor), `router.ts` (hash), `flow.ts`, `severity.ts`, `stack.ts`, `tree.ts`, `graphLayout.ts` |
| `src/components/ui/` | primitivos: `Button`, `Badge` (Chip, SeverityBadge, ModeBadge, Kbd, StatusDot), `Layout` (ScreenHeader, Section, Panel, DataList, Meter, Segmented), `States` |
| `src/components/domain/` | componentes del dominio (código, evidencia, grafos, riesgos, migración, Bob) |
| `src/components/domain/console/` | consola de la sesión: etapas en vivo, agentes de Bob, evidencia, pruebas y reproducción |
| `src/components/shell/` | app shell: barra superior, navegación, estado, paleta ⌘K, panel de Bob ⌘J |
| `src/views/` | una pantalla por sección; `JobGate` resuelve estados del análisis (privado, en curso, fallido) |

## Datos

Todo sale del backend (`src/api.ts`): `/api/audits*` (análisis, expediente, grafo, arquitectura, migración,
código fuente, descargas), `/api/audits/{id}/events?after=N` (actividad por etapas, con cursor), `/api/bob/status`
y `POST /api/audits/{id}/ask` (pregunta a Bob, exige token).
Los tipos de `src/types.ts` reflejan `backend/app/contracts/schema_v1.py`.
