# IBM Bob Usage Statement

Lablab.ai form field. Limit: 500 words. Only the text below the divider goes into the form. Every claim is
supported by `docs/bob-usage.md`.

---

IBM Bob 2.0 is CodeArchaeologist's analysis engine, and it was also a development tool used by the team during
the hackathon.

**Architecture.** The FastAPI backend invokes Bob Shell 2.0.5 with `bob run` through `subprocess`, using an
argument list and sending the prompt over stdin; repository text never enters the command line. Every session
runs against an isolated copy of the repository, without the evaluation ground truth or application secrets.
We read Bob's `stream-json` events and log to show what it reads, searches, and delegates in real time.

**Custom modes, subagents, and skills.** We created 11 modes in `.bob/custom_modes.yaml`, 18 subagents, and 24
skills. The product uses five modes:

- `evidence-auditor` is read-only and delegates in parallel to `legacy-sql-auditor`, `legacy-route-mapper`,
  `legacy-security-scanner`, and `legacy-dependency-tracer`. It returns JSON findings with file, lines, and a
  snippet; a Python validator rejects any citation that does not exist.
- `migration-architect` explains the three best cuts calculated by our deterministic engine. If it recommends
  a different cut or writes unsupported figures, its answer is rejected.
- `modernization-planner` and `modernization-surgeon` power the Modernization Studio: the first assesses the
  stack and creates a step-by-step plan; the second implements each step only inside a project copy.
- Bob's built-in `ask` mode answers user questions about the analyzed code.

**Controls.** Every session has turn, time, and bobcoin caps. If Bob exhausts its budget or loses the
connection before returning JSON, the pipeline resumes the same session with `--resume`, reserving a closing
turn inside the cap. Product figures—risk, migration order, and PERT effort—are calculated by code, never Bob.
The public deployment also has a daily bobcoin guard.

**How Bob helped us build it.** Relevant sessions, task IDs, and costs are recorded in `docs/bob-usage.md`.

- We used `--resume` to diagnose a large-ZIP audit whose four subagents exhausted the cap before producing a
  result; that led to automatic session recovery.
- We tested headless editing and discovered that `fileRegex` matches absolute paths. That finding shaped the
  Studio isolation boundary, which Bob then verified by writing inside its copy while three escape attempts
  were blocked.
- We explored `stream-json` to build live activity and used `ask` to test long chat responses.
- We recorded the real session used by the public showcase: four parallel subagents, 12 findings, 14 of 14
  valid evidence citations, 1.15 bobcoins, and 165 seconds.

Available per-member task-summary screenshots are tracked in `bob-sessions/`, with missing evidence called out
in its checklist so the submission cannot claim work that has not been documented.

**Execution honesty.** Every result says whether it comes from a `live` session or a real recorded session
(`imported`). The public showcase replays the recording at no cost. Live features are also open to judges
without an access token; the server uses its Bob API key under explicit spending limits.
