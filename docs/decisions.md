# Decisions

| ID | Decision |
|----|----------|
| D1 | The value is a validated dossier + a tested first cut, not a free-form report. |
| D2 | We are the decision layer that comes first; we complement IBM's modernization packages, we do not compete with them. |
| D3 | First cut = best value/risk ratio: `GET /invoices/{id}`. |
| D4 | P0 migration on the demo repo; P1 on arbitrary ZIP files. |
| D5 | DOCX is P0; a 6-slide PPTX is P1, from the same JSON. |
| D6 | Deterministic orchestrator in Python; Bob in bounded modes with subagents. |
| D7 | No figure without a measurement; risk = impact × uncertainty with criteria. |
| D8 | Execution mode always visible: `live`, `imported`, `example`. |
| D9 | Sample repos prepared beforehand and declared; product from the kickoff. |
| D10 | Only Python 3 + Flask + SQLite for the initial P0 MVP; architecture widened to polyglot for P1. |
| D11 | One container: FastAPI serves the API and the React build. Plan B: a tunnel. |
| D12 | If Bob does not run on the server: assisted mode importing JSON. |
| D13 | **Replaced by the Modernization Studio** (D37): the person picks targets such as NestJS, Spring Boot or Express and Bob implements the plan on a copy; there are no concept translation matrices. Original proposal: polyglot extensibility, cross migrations (FastAPI → NestJS, Express, Spring Boot) using concept translation matrices and characterization contracts. |
| D14 | **Discarded, not implemented** (see D38). Original proposal: shift-left risk gating, a blast radius simulator (`blast-radius-simulator`) before the PR, analyzing transitive call graphs and DB mutations without mutating code. |
| D15 | **Discarded, not implemented** (see D38). Original proposal: a multi-agent adversarial tribunal, a formal Architect vs. Skeptic (`code-skeptic`) dialectic to challenge assumptions, race conditions and hidden debt. |
| D16 | **Discarded, not implemented** (see D38). Original proposal: forensic git and AST mining, integrating PyDriller (churn hotspots vs. bugs) and Tree-sitter/AST for structural cartography and ER diagrams in Mermaid. |
| D17 | **Discarded, not implemented** (see D38). Original proposal: FastMCP external telemetry injection, a connector to DuckDB, read-only SQLite and GitHub to enrich static findings with production traffic and failure metrics. |
| D18 | Adopted the [official IBM Hackathon template](https://github.com/watsonxhackathon/ibm-hackathon-template): `.bobignore`, the security patterns in `.gitignore` and `SECURITY.md` are neither modified nor removed. |
| D19 | Rules update (2026-09-25): submission video ≤ 3:00 (previously ≤ 4:00), with ≥ 90 s of mandatory live demo; see `docs/submission/README.md`. |
| D20 | Rules update (2026-09-25): the repo must include screenshots of each team member's Bob session summary, in `bob-sessions/<person>/`; see `SECURITY.md` on how to take them without exposing credentials. |
| D21 | Rules update (2026-09-25): the submission form adds "Long Description" and "IBM Bob Usage Statement", both capped at 500 words; see `docs/submission/README.md`. |
| D22 | Audits that come from a ZIP are private: they never show up in the public listing. In locked mode (D40), the listing and every derived read require `X-Live-Token`; registered samples stay public. |
| D23 | The public showcase uses the versioned FacturaYa recording. The 15:22 run is not advertised as reproducible because its artifacts are not in the repository. |
| D24 | The memo is generated first with a narrative based only on data. A `board-narrator` narrative can only come in once a validator rejects any figure missing from the JSON. |
| D25 | Risk = severity weight × (1 + transitive callers). PERT depends on routes, functions, cited lines and affected complexity, with a visible formula and assumptions. |
| D26 | The first cut is a team reference implementation and only runs on registered samples. For user ZIP files `not_run` is reported; their code never runs. |
| D27 | The public API is `/api/audits`; the historical `/api/jobs` engine stays off and is not documented as a delivered capability. |
| D28 | Everything published about an analysis (activity feed, job error) is treated as public: absolute server paths are reduced to their final name and Bob failures arrive with a generic, actionable reason; stderr and the detail stay only in the server log. |
| D29 | The activity log is capped (5,000 events per analysis; above that only stage and closing events are written) and starting live audits is atomic (check and create under a lock): never two Bob sessions at once. |
| D30 | The route ranking and the roadmap by waves are deterministic: score = (value × testability) / risk (extended in D34); PERT per wave and per cut with an explicit heuristic warning ("Uncalibrated heuristic estimate"); the legacy /api/jobs engine is removed entirely. See `docs/migration-engine.md`. |
| D31 | Each Bob session is isolated deterministically (`backend/app/adapters/bob_workspace.py`): the modes that edit carry the `__WORK_ROOT__` marker in `fileRegex`, which fails closed until it is replaced with the workspace's absolute path (Bob matches against absolute paths) and rejects `..` segments; only read-only subagents travel to the workspaces; the Bob process never receives the app's secrets (only `BOB_*`). |
| D32 | Server responses carry CSP (`script-src 'self'`, no `unsafe-eval`), `X-Frame-Options: DENY`, `nosniff` and `Referrer-Policy: no-referrer`. "Modernization only" uploads (`modernize:`) are as private as audit uploads: they never show up in the public listing. |
| D33 | While Bob works, the interface shows what it really does (reads, searches, skills, subagents) from its stream: in the analysis console, in the Studio and in the chat (`GET /api/audits/{id}/ask/{request_id}/progress`). Never simulated progress. |
| D34 | The route score includes a business-data factor: `value × testability × data / risk`, with `data = 1` if the scope reads or writes any table and `0.5` otherwise. It applies D3 (a first cut visible to the business): without it, `POST /logout` came first because it held the CSRF evidence line. On the showcase, the engine recommends `GET /invoices`; the reference cut that runs is still `GET /invoices/{id}` (D3, D26), and the interface and the memo show the difference. |
| D35 | `migration-architect` only writes the qualitative reading of the ranking's top 3 candidates. A code validator requires one ranking endpoint per option, findings that candidate mitigates, zero figures and that the recommended option is the engine's; if it fails, there are no options (never templates). Cap: 6 turns, 1 bobcoin, no subagents. |
| D36 | The imported showcase is reused: opening it several times returns the same analysis as long as it has not failed. This keeps repeated visits from filling the public server's disk or CPU. |
| D37 | The Modernization Studio has a cap per implementation on top of the cap per step: `MODERNIZE_MAX_STEPS` (8 by default) and `MODERNIZE_TOTAL_MAX_COST` (6 bobcoins by default). Steps that do not fit are `skipped` with the reason. |
| D38 | Earlier material that does not describe the product (the `agent.yaml` manifest, contexts of discarded pillars, hourly plans, the first integration report) is archived in `docs/archive/` instead of being deleted. |
| D39 | Submission documents were written first in Spanish; superseded by D41. |
| D40 | `LIVE_AUDIT_TOKEN` is optional. Unset (the public demo): anyone can run live audits, Ask Bob and the Studio, so the judges need no token; spending is bounded by the per-run caps, one live audit and one question at a time, and the Bob account budget. Set: every Bob call and every read of an upload requires `X-Live-Token` (the kill switch). The frontend reads `live_requires_token` from `/api/bob/status` and only then shows token fields. An optional daily guard, `BOB_DAILY_SPEND_LIMIT` (15 on Render), pauses live features once the server has spent that many bobcoins in a UTC day; the showcase keeps working. |
| D41 | Product code, comments, UI, Bob prompts, tests, and current documentation are in English. The FacturaYa sample was synced with the English upstream repository while preserving the line structure, so recorded citations still validate. The recorded showcase originally ran in Spanish: its user-facing dossier was translated with ids, evidence, snippets, costs, and timings unchanged, while the raw recording remains historical input data. Replay processing exposes only sanitized English activity summaries, never the raw report bodies. |

## Kickoff answers (J-01)
1. **Technical scope**: the core starts with Flask + SQLite to FastAPI, extensible right away to NestJS and microservices through the catalog of specialized agents.
2. **Execution safety**: analyzed code is 100% data, never instructions (Prompt Defense Baseline active in every agent).
3. **Risk metrics**: computed by deterministic code in Python / AST, never invented by the language model.
