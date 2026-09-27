# Slide presentation outline

Required submission artifact. Nine slides, matching the video structure. Product figures come from the public
showcase. Market figures must have a citation on the slide; otherwise, omit them.

| # | Title | Content | Visual |
|---|---|---|---|
| 1 | CodeArchaeologist | "Where to start modernizing, backed by evidence." Built with IBM Bob 2.0. Team name and logo | Cover, reused as the submission cover image |
| 2 | The problem | Critical systems with no tests and no original author; boards must approve budgets without being able to read the code. Add a sourced technical-debt or legacy-maintenance figure only if verified | A monolith labeled "do not touch" |
| 3 | The solution | Three deliverables: verifiable dossier, calculated migration recommendation, and board memo. A tested first cut for the controlled sample | Three columns |
| 4 | How it works | Repository → Bob (`evidence-auditor` + four subagents) → evidence validator → deterministic engine (graph, SQL, complexity) → interface and memo | The README architecture diagram |
| 5 | IBM Bob at the center | 11 custom modes, 18 subagents, 24 skills; five product modes; live activity; caps and session recovery | Screenshot of **Bob session** |
| 6 | Evidence, not opinion | 12 validated findings and 14/14 verified citations in the showcase; every finding opens at the cited code | Screenshot of a finding and its code |
| 7 | What to migrate first | Formula `value × testability × data / risk`; recommended cut `GET /invoices`; avoid `/invoices/new` first; three PERT waves; reference cut passes 6/6 tests | Screenshot of **Recommendation and first cut** |
| 8 | Who it is for—and why us | CTOs, architects, consultancies, and boards. Difference: AI proposes and code decides; transparent `live` / `imported` execution; secure by design | Qualitative comparison with no invented competitor figures |
| 9 | Team and next step | Jean (product, DevOps, pitch), Felipe (Bob integration), Daniel (backend and metrics), Edgar (frontend and UX). Next: support more input stacks. Demo and repository links | Photos or avatars |

## Format

- Export to PDF for the form and keep the editable source.
- Follow the colors and typography in `DESIGN.md` so the deck matches the app.
- Do not include screenshots showing an API key, access token, personal data, or the Render dashboard.
