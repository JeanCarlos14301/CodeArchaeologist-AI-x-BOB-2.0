
# IBM Bob 2.0 usage and integration log

This document logs the IBM Bob Shell (`bob run`) sessions, the custom modes enabled in `.bob/custom_modes.yaml` and the multi-agent orchestration patterns Felipe implemented for the hackathon.

## Session log

Each row states its backing. Without a versioned `bob-result.json` or screenshot, the result is not a measurement.

| Date | Member | Mode / agent | Task | Result | Backing |
|---|---|---|---|---|---|
| 2026-09-24 19:30 | Felipe | `evidence-auditor` | F-01 / F-02: prompt defense calibration and schema v1 extraction | Unverified claim; must not be cited as a measured result. Original: validated, zero hallucinations on the demo repo | No verifiable artifact: no versioned `bob-result.json` or screenshot |
| 2026-09-24 20:15 | Felipe | `migration-architect` | F-04: drafting 3 Strangler Fig cuts on the Flask demo | Unverified claim; must not be cited as a measured result. Original: options computed with PERT estimate and blast radius | No verifiable artifact: no versioned `bob-result.json` or screenshot |
| 2026-09-24 20:50 | Felipe | `contract-keeper` | F-05: generating a characterization pytest suite for `/invoices/{id}` | Unverified claim; must not be cited as a measured result. Original: 100% green on the legacy endpoint | No verifiable artifact: no versioned `bob-result.json` or screenshot |
| 2026-09-24 21:20 | Felipe | `polyglot-architect` | F-10: mapping FastAPI → NestJS concepts and OpenAPI contracts | Unverified claim; must not be cited as a measured result. Original: Zod/class-validator translation matrix completed | No verifiable artifact: no versioned `bob-result.json` or screenshot |
| 2026-09-24 21:40 | Felipe | `blast-radius-guard` | F-11: simulation design on a hypothetical `db_pool.py` file | **Design, not run.** The file does not exist in FacturaYa and it is not presented as a measured result. | None: design, not run |
| 2026-09-24 21:55 | Felipe | `code-skeptic` | F-12: adversarial debate against a FastAPI migration proposal | Unverified claim; must not be cited as a measured result. Original: 3 concurrency and rollback vulnerabilities detected | No verifiable artifact: no versioned `bob-result.json` or screenshot |
| 2026-09-24 22:15 | Felipe | `git-archaeologist` | F-13: mining design on a hypothetical `legacy_db.py` file | **Design, not run.** The file does not exist in FacturaYa and no artifact backs a churn figure. | None: design, not run |
| 2026-09-25 13:20 | Felipe | `ask`, `evidence-auditor` | F-01 / F-02: installing Bob Shell 2.0.5 and smoke test with an API key through `BobAdapter` | Unverified claim; must not be cited as a measured result. Original: `status: success`, ~0.046 bobcoins per call; custom mode loaded from `.bob/custom_modes.yaml` | No verifiable artifact: no versioned `bob-result.json` or screenshot |
| 2026-09-25 13:45 | Felipe | `evidence-auditor` + subagents | Integrating `.bob/agents` and `.bob/skills`: live audit with delegation | Unverified claim; must not be cited as a measured result. Original: delegated to `legacy-sql-auditor`, `legacy-security-scanner` and `legacy-dependency-tracer` (Bob log); 12/12 findings and 18/18 valid evidence; 1.13 bobcoins, 189 s | No verifiable artifact: no versioned `bob-result.json` or screenshot |
| 2026-09-25 13:50 | Felipe | `evidence-auditor` | F-03: audit stages on FacturaYa (`python -m app.pipeline.run_audit`) | 13 findings, 16/16 valid evidence after the validator; 6/6 expected findings detected and 0 on the EF-7 control; 0.57 bobcoins, 87 s | `contracts/fixtures/bob-evidence-auditor-facturaya.json` (Bob's raw reply). Reproducible: `python evaluation/score.py` on the dossier that comes out of importing it gives 6/6, 0 false positives |
| 2026-09-25 15:22 | Jean | `evidence-auditor` (live, first run from a clean checkout, after installing Bob Shell 2.0.5 + Node 24) | Real audit of `facturaya-v1` from the interface | job `02833a24a7a7`: 13 findings reported, 12 validated, 16/17 valid evidence (94%), 1.14 bobcoins, 120 s. Against `expected-findings.json`: 5/6 expected findings detected and validated, 1 (`EF-3`, duplicated discount) detected by Bob but rejected by the validator (the `reports.py` evidence did not match), 0 false positives on the `EF-7` control. Details in `evaluation/README.md`. Full artifacts (copied workspace, `bob-result.json`, `dossier.json`) in `artifacts/jobs/02833a24a7a7/` (not versioned; they stay on Jean's machine) | Local artifacts, not versioned (`artifacts/jobs/`) |
| 2026-09-26 00:09 | Felipe | `ask` (`--format stream-json`) | Testing the real-time event format on two files | Emits `message`, `tool_use`, `tool_result` and `result`; 0.14 bobcoins | Local artifacts, not versioned (`artifacts/jobs/`) |
| 2026-09-26 00:09 | Felipe | `evidence-auditor` (`--resume`) | Diagnosing the failure of `upload:proyecto_ciber-main.zip` (job `2f944b585cdb`) | Bob exhausted the 5-bobcoin cap (its 4 subagents spent 3.89) without delivering the JSON; "No files found" was its last search. Resuming the session delivered the JSON for 0.17 bobcoins (15 findings, 13 validated). Not published: the sandbox excluded `tests/` and Bob falsely reported "no tests" (fixed) | Local artifacts, not versioned (`artifacts/jobs/`) |
| 2026-09-26 00:18 | Felipe | `evidence-auditor` (live, stream) | First audit with live activity (job `6a3ed667018e`) | The inference service cut the stream (`read ETIMEDOUT`) at 154 s. The session, located by its workspace, was resumed and delivered a valid JSON (0.68 bobcoins in total). It motivated the automatic rescue | Local artifacts, not versioned (`artifacts/jobs/`) |
| 2026-09-26 00:25 | Felipe | `evidence-auditor` + 4 subagents (live, stream) | Recording of the showcase (job `0234884643c5`) | Delegated in parallel to `legacy-sql-auditor`, `legacy-route-mapper`, `legacy-security-scanner` and `legacy-dependency-tracer` (0.04–0.11 bobcoins each); 12/12 findings, 14/14 valid evidence, first cut 3/3; 1.15 bobcoins, 165 s. Against `expected-findings.json`: 5/6 (EF-3 detected as F-7 but citing the constants, not the calculation). This is the session the showcase replays (its findings' prose was translated to English afterwards; see `contracts/README.md`) | Local artifacts, not versioned (`artifacts/jobs/`); result and activity versioned in `contracts/fixtures/` |
| 2026-09-26 00:30 | Felipe | `evidence-auditor` (live, stream) | Run with the "cite the line where the problem happens" rule (job `b7424d9733a6`) | Bob did not delegate (it read the 12 files); 10/10 findings, 13/13 evidence; 1.44 bobcoins, 126 s. 5/6: it detected EF-3 and did not report EF-2 (variability between runs) | Local artifacts, not versioned (`artifacts/jobs/`) |
| 2026-09-26 11:05 | Felipe | `evidence-auditor` (terminal) | Evidence of use from the terminal (task `39094ee2b09c`) | Listed FacturaYa's `.py` files and explained `app.py:16`; 0.18 bobcoins, 10.4 s | `bob-sessions/felipe/2026-09-26_F-15_bob-run-terminal.png` |
| 2026-09-26 11:32 | Felipe | test mode with `edit` (`fileRegex: ^out/`) | Can Bob write headless? (task `b68246e69cd8`) | It blocked ALL writes: Bob matches `fileRegex` against the **absolute path**, so a relative regex never matches; 0.21 bobcoins | Session in `~/.bob/db/bob.db` (local) |
| 2026-09-26 11:33 | Felipe | same mode, regex anchored to the workspace's absolute path | Repeat (task `332d224a3f21`) | Wrote `out/main.py` (Flask → FastAPI) and blocked `src/extra.py`, outside the allowed path; 0.21 bobcoins | Session in `~/.bob/db/bob.db` (local) |
| 2026-09-26 15:49 | Felipe | `ask` | QA of the chat overflow with a long answer (task `00068c506f1a`) | Structured answer in 13 s; 0.21 bobcoins | Session in `~/.bob/db/bob.db` (local) |
| 2026-09-26 16:05 | Felipe | `modernization-surgeon` with the regex rendered by `bob_workspace.py` | Checking the isolation after the security audit (task `27fb3e19d09b`) | Wrote `main.py` in its copy and all three attempts to get out were blocked: an absolute path outside the copy, `../escape.txt` and `.bob/custom_modes.yaml`. The Bob process no longer receives `LIVE_AUDIT_TOKEN` or other keys; 0.36 bobcoins | Session in `~/.bob/db/bob.db` (local) |
| 2026-09-26 16:18 | Felipe | `ask` (`--format stream-json`) | Chat with Bob's live activity (task `4e7d6ce0ef17`) | Progress through `GET /ask/{id}/progress` showed Bob searching for `auth.py` and `app.py`, reading them and reasoning before answering; 9 steps, 0.17 bobcoins, ~24 s | Session in `~/.bob/db/bob.db` (local) |
| 2026-09-26 20:53 | Felipe | `polyglot-architect` (terminal) | FacturaYa's current stack and a suitable modernization target (task `eaacf5cf39db`) | Identified Flask 3.1 + SQLite + cookie sessions and proposed FastAPI, SQLAlchemy 2 + Alembic, and JWT; flagged SQL injection at `app.py:78`; 5 tool calls, 0.251 bobcoins, 19.7 s | `bob-sessions/felipe/2026-09-26_polyglot-architect.png` |
| 2026-09-26 20:54 | Felipe | `modernization-planner` (terminal) | Three-step FacturaYa modernization plan (task `18f5ac81623b`) | 1) Parameterized SQL (critical), 2) secrets in environment variables (high), 3) unified discount logic between `billing.py:28` and `reports.py:12-16` (medium); 7 tool calls, 0.251 bobcoins, 24.8 s | `bob-sessions/felipe/2026-09-26_modernization-planner.png` |
| 2026-09-26 19:06 | Daniel | `blast-radius-guard` (Bob IDE terminal) | Static blast radius attempt on `db.py` (task `4a259689353b`) | Activated `blast-radius-simulation` and inspected `db.py`, `app.py`, `auth.py`, `customers.py`, `reports.py`, and `utils.py`; 9 tool calls, 0.068 bobcoins, 8.3 s. The run hit its three-turn limit with zero assistant messages. | `bob-sessions/daniel/2026-09-26_blast-radius-guard01.png`, `bob-sessions/daniel/2026-09-26_blast-radius-guard02.png` |
| 2026-09-26 21:15 | Daniel | `blast-radius-guard` (Bob IDE terminal) | Complete static blast radius analysis on `samples/facturaya-v1/db.py` (`connect()`, `get_db()`, `invoice_by_id()`) (task `4420fca2456d`) | Activated `blast-radius-simulation` skill; executed 16 tool calls across project files; delivered executive risk table, guaranteed test regression list, symbol inventory (33 functions across 8 modules), transitive call graphs, DB mutation matrix, quantitative impact metrics (DIR: 30.3%, TBR: 66.7%, CBRS: 73.2/100 RED GATE automated block verdict), and Mermaid failure propagation flowchart; 3 assistant messages, 0.323 bobcoins, 1m 16s | `bob-sessions/daniel/2026-09-26_blast-radius-guard-extended-01.png` to `06.png` |
| 2026-09-26 | Jean | `migration-architect` (Bob IDE terminal) | Which FacturaYa route to migrate first with the Strangler Fig pattern, citing files and lines | Used the `legacy-audit-workflow` skill, read the sample's modules and delivered a route inventory and decision matrix; recommended `GET /invoices/<int:invoice_id>` (`app.py:91-107`) as the first cut; 0.291 bobcoins | `bob-sessions/jean/bob-sessions01-jean-migration-architect.PNG` to `04` |
| 2026-09-26 | Edgar | `code-skeptic` (Bob IDE terminal) | False assumptions in `samples/facturaya-v1/billing.py` total calculation | Listed assumptions with file:line citations: fixed rate used as a discount, `int()` truncation of quantities, zero unit prices, double rounding in `amount()`, race in invoice numbering (`billing.py:45-46`); 0.110 bobcoins at the time of the screenshot | `bob-sessions/edgar/bob-sessions-01-edgard.jpeg` to `03` |

### Scoring against the ground truth
`python evaluation/score.py <dossier.json>` applies a single rule: an expected finding is a hit if a **validated** finding
overlaps its lines in the same file; rejected findings do not count. With the only versioned run (25/09 13:50) it gives 6/6.
The **5/6** cited for Jean's run (`02833a24a7a7`) and Felipe's runs (`b7424d9733a6`, `0234884643c5`) **cannot be reproduced**
with data in the repo: their `dossier.json` files are not versioned. To back them, those dossiers (without credentials) have to be
uploaded to `contracts/fixtures/`.

## Registered custom modes (`.bob/custom_modes.yaml`)

Four custom modes are invoked from the code: `evidence-auditor` and `migration-architect` in the analysis
(`backend/app/pipeline/evidence_audit.py`), and `modernization-planner` and `modernization-surgeon` in the
Modernization Studio (`backend/app/modernization/`). The "Ask Bob" chat uses the built-in `ask` mode
(`backend/app/jobs/assistant.py`). The rest are defined but **not wired to any flow**.

| Slug | Name | Permissions | Goal | Wired into the pipeline |
|---|---|---|---|---|
| `evidence-auditor` | Evidence Auditor | `read` | Forensic inspection with file and line evidence (schema v1). | Yes |
| `migration-architect` | Migration Architect | `read` | Qualitative reading of the deterministic ranking's top 3 cuts; a validator rejects figures and cuts other than the engine's pick. | Yes, live audits only (`backend/app/pipeline/migration_architect.py`); the imported showcase does not invoke it |
| `contract-keeper` | Contract Keeper | `read, edit` | Writing golden-master characterization tests with pytest. | No |
| `strangler-surgeon` | Strangler Surgeon | `read, edit, command` | Implementing the new modern cut under `modern/` behind a facade. | No |
| `board-narrator` | Board Narrator | `read` | Writing the executive memo for the board without inventing figures. | No |
| `polyglot-architect` | Polyglot Architect | `read` | Mapping types and patterns across stacks (FastAPI ↔ NestJS ↔ Spring Boot). | No |
| `blast-radius-guard` | Blast Radius Guard | `read` | Static pre-PR simulation of blast radius and cascading failures. | No |
| `code-skeptic` | Code Skeptic | `read` | Adversarial tribunal to stress and validate technical proposals. | No |
| `git-archaeologist` | Git Archaeologist | `read, command` | Forensic mining of git repositories with PyDriller. | No |
| `modernization-planner` | Modernization Planner | `read` | Modernization Studio: feasibility, trade-offs and a step-by-step plan for any stack. | Yes (`backend/app/modernization/planner.py`); no live run logged |
| `modernization-surgeon` | Modernization Surgeon | `read, edit` (no `execute`) | Modernization Studio: runs one plan step on a copy of the project. | Yes (`backend/app/modernization/implement.py`); no live run logged |

## Invocation from Python

`BobAdapter.run` (`backend/app/adapters/bob_adapter.py`) runs `bob run --format json --mode <mode> --workspace <path> --max-turns N --max-cost N --trust`
with an **argument list, no `shell=True`**, and hands the prompt over **stdin**; the repository's text never enters the command line.
Since the English submission, every prompt asks Bob to write its findings and answers in English.

## Orchestration patterns (design, not run)

None of these flows is implemented or measured. They are kept as a proposal.

- **Adversarial tribunal** (`migration-architect` proposes, `code-skeptic` objects, verdict in 4 rounds).
- **Shift-left pre-PR gate** (`blast-radius-guard` with a composite blast radius score). The CBRS score that used to appear here does not exist in the product: the real risk is `risk_matrix` (`backend/app/pipeline/decision_metrics.py`).

## Installing and running Bob Shell

```bash
curl -fsSL https://bob.ibm.com/download/bobshell.sh | bash -s -- --pm npm   # requires Node 24+
cp .env.example .env    # and fill in BOB_API_KEY (scope: Inference)
```

The first run requires accepting the IBM license (`bob` interactively, or `--accept-license`).
The pipeline invokes Bob only through `backend/app/adapters/bob_adapter.py`:

```python
from pathlib import Path
from app.adapters.bob_adapter import BobAdapter
result = BobAdapter(Path("samples/facturaya-v1")).run("evidence-auditor", prompt)
```

Tests: `cd backend && pytest` (the `live` test is skipped when there is no `bob` or `BOB_API_KEY`).

### End-to-end evidence audit

```bash
cd backend
python -m app.pipeline.run_audit ../samples/facturaya-v1          # live
python -m app.pipeline.run_audit <repo> --import ../contracts/fixtures/bob-evidence-auditor-facturaya.json  # imported
```

The repo is copied to `artifacts/jobs/<id>/workspace` without `evaluation/` or `expected-findings*.json`,
so Bob never sees the evaluation material. The output lands in `artifacts/jobs/<id>/dossier.json`.

### How Bob Shell discovers the project's assets (verified on 2.0.5)
- Subagents: `.bob/agents/*.md`. Line-by-line frontmatter: `name`, `description` on **a single line**,
  `groups` (list), optional `modelTier` (`fast|premium|ultra|explorer`). **`model:` makes Bob drop the agent.**
- Skills: `.bob/skills/<name>/SKILL.md`, with `name` equal to the folder.
- Commands: Bob turns `.bob/commands/*.md` into `.bob/skills/<name>/` at startup (and overwrites skills with the same
  name), which is why the commands live directly as skills with `user-invocable: true`.
- Valid groups in modes and subagents: `read, edit, execute, browser, mcp, skill, todo, subagent, mode`.
  A mode needs `subagent` to delegate and `skill` to activate skills.
- Bob also loads global skills from `~/.bob/skills`, `~/.agents/skills` and `~/.claude/skills`.

### Live activity and session rescue (verified on Bob Shell 2.0.5)

- `bob run --format stream-json` emits on stdout `message` (assistant text in chunks), `tool_use`,
  `tool_result` and `result`. The `result` carries no `last_message`: the final message is rebuilt from the text
  after the last tool call (`BobAdapter.run_stream`).
- `tool_use` and `tool_result` arrive **when the tool finishes**: parallel `spawn_subagent` calls show up together
  once every subagent is done.
- `cost`, `subagent_start` and `subagent_end` (with each subagent's tools, turns, duration and cost)
  **only go to the log** `~/.bob/logs/shell/bob-shell-*.log`. `BobLogTail` follows the session's log (the one that
  mentions its workspace) to show them in real time.
- `bob run --resume <task_id>` first replays the history (from the original prompt) and then processes the new
  prompt; `--max-cost` is cumulative for the whole session.
- Sessions are stored in `~/.bob/db/bob.db` (table `tasks`, `env.workspace`): if the stream is cut before the
  `result`, `BobAdapter.find_session_id` locates the session to resume it.
- The pipeline reserves 20% (max 1 bobcoin) of `BOB_MAX_COST` to close the session: if Bob exhausts the exploration or
  the connection drops without JSON, it resumes it with a turn that only asks for the result. The total cost never
  exceeds `BOB_MAX_COST`.
- The activity of each stage is stored in `artifacts/jobs/<id>/events.jsonl` and served with
  `GET /api/audits/{id}/events?after=N`. The showcase replays `contracts/fixtures/bob-events-facturaya.jsonl`.
- On shutdown, the server terminates the running Bob sessions (`terminate_active_sessions`): a restart leaves no
  process spending bobcoins.
