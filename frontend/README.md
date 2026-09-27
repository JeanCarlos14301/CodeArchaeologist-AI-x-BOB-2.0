# Frontend

Modernization workspace (Vite + React 19 + TypeScript + Tailwind 4), served by FastAPI from `dist/`.

- **Design:** [../DESIGN.md](../DESIGN.md) (tokens, components, rules). **Product:** [../PRODUCT.md](../PRODUCT.md).
- **Owner:** Edgar (E-01 to E-08).

## Usage

```bash
npm install
npm run dev     # http://localhost:5173 with a proxy for /api and /health to http://127.0.0.1:8000
npm run build   # builds dist/, which FastAPI serves at http://127.0.0.1:8000
```

## Structure

| Folder | Contents |
|---|---|
| `src/styles/tokens.css` | primitive (`--ca-*`) and semantic (`@theme`) tokens; Tailwind's default palettes are disabled |
| `src/lib/` | state and domain logic without UI: `workspace.tsx` (provider), `router.ts` (hash), `flow.ts`, `severity.ts`, `stack.ts`, `tree.ts`, `graphLayout.ts` |
| `src/components/ui/` | primitives: `Button`, `Badge` (Chip, SeverityBadge, ModeBadge, Kbd, StatusDot), `Layout` (ScreenHeader, Section, Panel, DataList, Meter, Segmented), `States` |
| `src/components/domain/` | domain components (code, evidence, graphs, risks, migration, Bob) |
| `src/components/domain/console/` | the session console: live stages, Bob's agents, evidence, tests and replay |
| `src/components/shell/` | app shell: top bar, navigation, status bar, ⌘K palette, ⌘J Bob panel |
| `src/views/` | one screen per section; `JobGate` resolves the analysis states (private, running, failed) |

## Data

Everything comes from the backend (`src/api.ts`): `/api/audits*` (analyses, dossier, graph, architecture, migration,
source code, downloads), `/api/audits/{id}/events?after=N` (per-stage activity, by cursor), `/api/bob/status`
and `POST /api/audits/{id}/ask` (ask Bob; spends bobcoins).
The access token is only requested when the server sets `LIVE_AUDIT_TOKEN` (`bob.live_requires_token`); otherwise the
UI hides every token field.
The types in `src/types.ts` mirror `backend/app/contracts/schema_v1.py`.
