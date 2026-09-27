# Long Description

Lablab.ai form field. Limit: 500 words. Only the text below the divider goes into the form.

---

Every mature company has a system nobody dares to touch. It keeps the business running, but its author is
gone, it has no tests, and every change is a gamble. When the board asks, "How much will modernization cost,
and where should we start?", the answer is usually a weeks-long consultancy or an unsupported opinion.

CodeArchaeologist answers that question in minutes, with evidence. It takes a legacy repository (Python 3,
Flask, and SQLite in this version) and produces three deliverables:

1. **A verifiable technical dossier.** IBM Bob audits the code in read-only mode and delegates to specialized
   subagents for SQL, routes, security, and dependencies. Every finding cites a file, line range, and snippet.
   A Python validator confirms that the citation exists literally in the code; findings that do not match are
   rejected. Nothing enters the dossier without evidence.
2. **An auditable migration recommendation.** A deterministic engine walks the call graph, SQL queries, and
   route complexity, then calculates what to migrate first using a visible formula: value × testability ×
   business data / risk. It proposes the first cut, alternatives, the route not to tackle first, and a
   three-wave roadmap with PERT effort. Code calculates the numbers; AI does not.
3. **A board-ready DOCX memo** containing the decision, risk matrix, recommendation, and traceability from
   every figure back to the code.

For the controlled FacturaYa sample, CodeArchaeologist also runs a first Strangler Fig cut: the legacy route
and its modern replacement pass the same characterization suite (6 of 6 tests). User-uploaded code is never
executed; it is analyzed statically.

In the Modernization Studio, Bob proposes a step-by-step plan and applies it to an isolated copy of the
project, under explicit spending caps.

**Who it is for.** CTOs and architecture teams inheriting critical systems; consultancies that need a
defensible assessment before quoting; and boards that must approve modernization budgets without reading code.

**What makes it different.**

- *Evidence before narrative.* Every claim opens at the cited code. In the public showcase, all 14 citations
  pass validation.
- *AI proposes; code decides.* Bob discovers and explains. Reproducible code calculates risk, migration order,
  and effort. If Bob contradicts the engine or invents a figure, its response is rejected.
- *Execution transparency.* Every result is labeled `live` or `imported`, and the interface shows what Bob
  reads, searches, and delegates in real time.
- *Secure by design.* The analyzed repository is data, never instructions. Uploaded audits are not publicly
  listed, and uploaded code never runs.

The public demo opens without credentials and replays a real IBM Bob audit of FacturaYa: 12 validated
findings, a migration recommendation, a tested first cut, and a downloadable memo. Judges can also run live
features without an access token; the server uses its configured Bob API key and enforces per-run and daily
spending limits.

CodeArchaeologist does not replace the modernization team. It gives them the map, the order, and the evidence
to start on Monday.
