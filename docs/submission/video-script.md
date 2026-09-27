# Video script (maximum 3:00, MP4)

Judging rules: nothing after 3:00 counts; show the working solution for at least **90 seconds**; include
narration and a clear demonstration of IBM Bob. Keep the `live` / `imported` label visible during the demo.

**Before recording:** open the public URL two minutes early in case the Render instance is asleep; use an
incognito window at 110% browser zoom; hide tabs, bookmarks, and personal data. Never show the API key, an
access token, or the Render dashboard.

## Scenes

| Time | Length | Scene | What is shown | Draft narration |
|---|---:|---|---|---|
| 0:00–0:20 | 20 s | Problem | Slides 1–2: a ten-year-old billing monolith with no tests | "Every company has a system nobody dares to touch. When the board asks how much modernization will cost and where to start, nobody has an evidence-backed answer." |
| 0:20–0:30 | 10 s | Solution in one sentence | Slide 3: the three deliverables | "CodeArchaeologist uses IBM Bob to audit the code and produces a verifiable dossier, a calculated migration recommendation, and a board-ready memo." |
| 0:30–0:50 | 20 s | **Demo 1 · Bob at work** | Home → **FacturaYa · ready-made** → open the analysis. In **Bob session**, select *Replay session* to show the plan, reads, and four delegated subagents | "This is a real Bob session on FacturaYa. The evidence-auditor mode plans the work, reads the code, and delegates in parallel to SQL, route, security, and dependency specialists." |
| 0:50–1:15 | 25 s | **Demo 2 · Evidence** | **Risks**: open F-1 (SQL injection), then show its highlighted source and "14/14 citations verified" | "Every finding cites a file and exact lines. A Python validator confirms that the citation exists literally in the code. If it does not match, the finding is discarded." |
| 1:15–1:45 | 30 s | **Demo 3 · What to migrate first** | **Modernization → Recommendation and first cut**: `GET /invoices`, formula, `/invoices/new` warning, and PERT waves | "Where should we start? The engine walks the call graph and SQL, then calculates value times testability times business data over risk. It recommends GET invoices and warns against invoices new: that route concentrates findings and writes to two tables. Code calculates the numbers; AI does not." |
| 1:45–2:05 | 20 s | **Demo 4 · Tested first cut** | Same view: legacy and modern code side by side; 6/6 tests green | "For the controlled sample, we run a first Strangler Fig cut. The legacy route and modern replacement pass the same characterization tests." |
| 2:05–2:25 | 20 s | **Demo 5 · Ask Bob live** | Bob panel: ask "What should I migrate first, and why?"; show Bob reading files in real time | "Anyone evaluating the app can ask Bob about the code. This request is live, and we can see which files Bob reads before it answers." |
| 2:25–2:40 | 15 s | **Demo 6 · Board memo** | **Reports**: download and open the DOCX at **Migration recommendation** | "The analysis ends in a board-ready memo, with the decision and a traceable path from every figure back to the code." |
| 2:40–3:00 | 20 s | Value and close | Slides 8–9: audience, differentiation, team | "CodeArchaeologist does not replace the modernization team. It gives them the map, the order, and the evidence to start on Monday. Built with IBM Bob 2.0." |

On-screen demo from 0:30 to 2:40 totals **130 seconds**; the required minimum is 90 seconds.

## Notes

- Demo 5 is the only scene that spends bobcoins (less than one under the configured cap). It requires no
  access token in the public deployment. If Bob does not answer quickly enough during recording, show the
  Modernization Studio instead, or extend Demo 3.
- The showcase is labeled `imported`. Say "real recorded session" aloud; do not present it as live.
- Show only figures visible in the app. If the recorded session changes, update the figures in this script.
- Export at 1080p, verify the final duration is no more than 3:00, and upload it using the public or unlisted
  hosting option required by the form.
