# Archive: earlier material that is not part of the product

For transparency, this directory preserves design and planning material produced during the hackathon that
**does not describe what CodeArchaeologist does today**. The product neither imports nor uses it. It lives here
so the submission does not present unimplemented ideas as features.

| File | What it is | Why it is archived |
|---|---|---|
| `agent.yaml` | Manifest from an experiment with an agent and skill catalog. | Neither Bob nor the backend loads it. It mentions models and "pillars" that are not part of the product. |
| `contexts/` | Contexts for proposed pillars such as an adversarial tribunal, risk simulation, and polyglot migration. | Those pillars were dropped; see `docs/decisions.md`. No product code uses them. |
| `bob-session-report.md` | Technical report from the first Bob integration. | It describes dropped pillars as implemented, including CBRS, FastMCP, PyDriller, and the tribunal. The current evidence-backed record is `docs/bob-usage.md`. |
| `planning/tasks.md` and `planning/create_issues.sh` | Hour-by-hour event plan and the script that created issues from it. | Internal planning that has already been executed. |
| `planning/fix-plan-26-09.md` | September 26 correction plan. | Internal planning that has already been executed. |

Current product documentation is in the root [README](../../README.md),
[docs/migration-engine.md](../migration-engine.md), and [docs/bob-usage.md](../bob-usage.md).
