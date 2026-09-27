# IBM Bob session evidence

Screenshots of IBM Bob sessions run by each team member from their own account during the hackathon. Every session
used a mode from this repository's [.bob/custom_modes.yaml](../.bob/custom_modes.yaml) against the
[FacturaYa sample](../samples/facturaya-v1/). The full session log, with task IDs and costs, is in
[docs/bob-usage.md](../docs/bob-usage.md).

| Member | Mode | What Bob did | Cost | Evidence |
|---|---|---|---|---|
| **Felipe** | `evidence-auditor` | Headless `bob run` from the terminal: listed FacturaYa's modules and explained `app.py:16` (task `39094ee2b09c`) | 0.180 | [felipe/2026-09-26_F-15_bob-run-terminal.png](felipe/2026-09-26_F-15_bob-run-terminal.png) |
| | `polyglot-architect` | Identified FacturaYa's stack and proposed a modernization target (task `eaacf5cf39db`) | 0.251 | [felipe/2026-09-26_polyglot-architect.png](felipe/2026-09-26_polyglot-architect.png) |
| | `modernization-planner` | Three-step modernization plan for FacturaYa (task `18f5ac81623b`) | 0.251 | [felipe/2026-09-26_modernization-planner.png](felipe/2026-09-26_modernization-planner.png) |
| | `board-narrator` | Executive narrative for the board (task `2c12a3e21954`) | 0.238 | [felipe/2026-09-26_board-narrator.png](felipe/2026-09-26_board-narrator.png) |
| | `evidence-auditor` in the app | The live session replayed by the public showcase: 4 subagents, 12 findings | 1.15 | [felipe/2026-09-26_F-03_live-session-evidence-auditor.png](felipe/2026-09-26_F-03_live-session-evidence-auditor.png) |
| **Daniel** | `blast-radius-guard` | Blast radius of `db.py`: call graphs, mutation matrix and impact metrics (task `4420fca2456d`) | 0.323 | [daniel/](daniel/) (6 screenshots, described in [daniel/README.md](daniel/README.md)) |
| **Jean** | `migration-architect` | Which route to migrate first with the Strangler Fig pattern, with a decision matrix and file:line citations | 0.291 | [jean/](jean/) (4 screenshots) |
| **Edgar** | `code-skeptic` | Review of false assumptions in `billing.py` total calculation, with file:line citations | 0.110 (while running) | [edgar/](edgar/) (3 screenshots) |

Costs are in bobcoins, as shown by Bob. Every screenshot was reviewed so that no API key, token or other credential
is visible ([SECURITY.md](../SECURITY.md)).
