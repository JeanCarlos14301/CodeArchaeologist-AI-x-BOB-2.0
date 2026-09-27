# IBM Bob session screenshots (required deliverable)

The hackathon rules require the public repository to include a **Bob Task Session Summary screenshot from
each team member**, captured from that member's own account. This directory is versioned and is not ignored by
`.gitignore`.

## Status by team member

| Member | Directory | Status |
|---|---|---|
| Felipe | [felipe/](felipe/) | ✅ Four terminal `bob run` Task Summaries, each with a different mode: `2026-09-26_F-15_bob-run-terminal.png` (`evidence-auditor`, 0.180 bobcoins, task `39094ee2b09c`), `2026-09-26_polyglot-architect.png` (0.251, task `eaacf5cf39db`), `2026-09-26_modernization-planner.png` (0.251, task `18f5ac81623b`), and `2026-09-26_board-narrator.png` (0.238, task `2c12a3e21954`). `2026-09-26_F-03_live-session-evidence-auditor.png` shows the showcase's live session in the app (1.15 bobcoins). |
| Jean | [jean/](jean/) | ⚠️ `EVIDENCE-USEBOB-001.PNG`: Bob Shell 2.0.5 Task Overview (task `c54cdc15907f`, September 25) with zero bobcoins for that task. A screenshot from a task with nonzero cost is still required. |
| Daniel | [daniel/](daniel/) | ✅ Six terminal screenshots `2026-09-26_blast-radius-guard-extended-01.png` to `06.png` (`blast-radius-guard`, task `4420fca2456d`, 0.323 bobcoins, 1m 16s). Shows complete static blast radius analysis of `samples/facturaya-v1/db.py`, tool executions, symbol inventory, transitive call graphs, mutation matrix, quantitative impact metrics (DIR: 30.3%, TBR: 66.7%, CBRS: 73.2/100 RED GATE), failure propagation Mermaid diagram, and complete Task Summary. |
| Edgar | [edgar/](edgar/) | ❌ The directory is empty. The screenshot is missing. |

## What every screenshot must show

The judges need evidence that **each member used Bob from their own account**. Every screenshot must include:

1. The `bob run --mode <mode> …` command (or the interactive session), using a mode from this repository.
2. Bob's response about real project code.
3. The complete **Task Summary** block: a bobcoin cost **greater than zero**, duration, and Task ID.

A pytest screenshot, browser screenshot, or task with zero bobcoins does not count as a session summary.

## Recommended session for each member

Each member uses a different read-only, cost-capped mode tied to their work so the combined evidence shows
real use of the repository's modes. Run these commands from the repository root.

| Member | Why this mode | Command |
|---|---|---|
| **Jean** (product, deployment, pitch) | It explains which cut should be migrated first—the core of the pitch. | `bob run --mode migration-architect --max-turns 6 --max-cost 0.6 --trust "Do not modify files. In samples/facturaya-v1, which route would you migrate first with the Strangler Fig pattern, and why? Cite files and lines."` |
| **Daniel** (backend and contract) | ✅ Completed (`blast-radius-guard`, task `4420fca2456d`, 0.323 bobcoins). Full analysis across 6 screenshots in [daniel/](daniel/). | — |
| **Edgar** (frontend) | A skeptical code review that challenges assumptions before migration. | `bob run --mode code-skeptic --max-turns 4 --max-cost 0.4 --trust "Do not modify files. Review samples/facturaya-v1/billing.py and identify assumptions in total calculation that may be false. Cite files and lines."` |
| **Felipe** (Bob modes) | ✅ Already complete (`evidence-auditor`, `polyglot-architect`, `modernization-planner`, and `board-narrator`). No repeat needed. | — |

If `bob run` is unavailable, an interactive session is acceptable: run `bob`, choose the mode with `/mode`,
ask the same question, and close the session so the summary appears.

## How to save it

1. Capture the full terminal, including command, response, and Task Summary. If the response is long, use two
   screenshots: one showing the command and one showing the summary.
2. Save it as `bob-sessions/<member>/YYYY-MM-DD_<mode>.png`, for example
   `bob-sessions/daniel/2026-09-26_blast-radius-guard.png`.
3. Add a row to `docs/bob-usage.md` with the date, member, mode, task, cost, and Task ID.
4. Update the status table above.

## Before committing a screenshot

Follow [SECURITY.md](../SECURITY.md): crop or blur anything outside the session summary. In particular, no API
key, access token, or other credential may be visible, including fields in the app or Render dashboard.
`.bobignore` prevents Bob from recording credential patterns, but screenshots still require manual review. A
visible email address is not a credential, though the member may blur it for privacy.

The full session log is in [docs/bob-usage.md](../docs/bob-usage.md).
