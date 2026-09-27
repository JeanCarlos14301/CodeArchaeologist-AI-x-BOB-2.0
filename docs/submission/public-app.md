# Publishing the app for the judges

How to leave the public URL ready for lablab.ai without exposing credentials, without making the judges ask for a
token and without running out of bobcoins in the middle of judging.

## 1. What every visitor sees (open mode)

| Path | Needs a token? | Spends bobcoins? |
|---|---|---|
| Home → **FacturaYa · already generated** → **Open the FacturaYa analysis** (imported showcase) | No | No |
| Walking the showcase: overview, Bob session, risks, architecture, migration recommendation, tested first cut, DOCX memo | No | No |
| Ask Bob about an analysis (⌘J panel) | No | Up to 0.8 per question |
| Home → **Upload ZIP** → **Audit with evidence** | No | Up to ~4 per audit |
| Home → **Upload ZIP** → **Modernization only** | No | Not on upload; yes when using the Studio |
| Modernization Studio (assess, plan, implement) | No | Up to ~9 per full run |

The showcase replays a real Bob session recorded on September 26 (12 findings, 14/14 evidence, 1.15 bobcoins when it
was recorded) and shows it with the `imported` label. Everything the judges need to evaluate the product works with
**no token and no spending**; the live features work too, with no token, within the caps below.

## 2. Bob API key

- **Whose:** Daniel's. Before submitting, check that his account has budget left: run `bob` and read the task summary
  (*Monthly Budget* / *Monthly Usage*).
- **Where:** only in Render → *Environment* → `BOB_API_KEY`. Never in the repo, in the video, in screenshots or in
  the lablab.ai form.
- **That account's monthly budget is the global ceiling:** if it runs out, live features stop working, but the
  showcase stays up because it never calls Bob.
- **When to swap it:** if the account drops below ~10 bobcoins during judging, paste another member's key into Render
  (it redeploys by itself in ~1 minute, with no code change).

## 3. Access: open mode, with a kill switch

The public deployment runs **without `LIVE_AUDIT_TOKEN`** (D40). That way there is no token to hand over and nothing
depends on reaching the judges: they can upload their own repository, ask Bob and use the Studio right away.

- The form and the video say that live features spend real bobcoins and are capped; nothing else is needed.
- Uploaded repositories stay unlisted: they never show up in the public listing and are reachable only through their
  random job id. Open mode is a judging convenience, not authentication; use the kill switch for stricter access.
- **Kill switch:** if someone abuses the URL, add `LIVE_AUDIT_TOKEN` with a long random value in Render →
  *Environment* (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). About a minute later every Bob call
  requires the token and the interface shows the token fields. The showcase keeps working. Remove the variable to
  reopen.
- If the earlier blueprint created `LIVE_AUDIT_TOKEN` in Render, **delete it** in *Environment*: removing it from
  `render.yaml` does not delete it from an existing service. Check `GET /api/bob/status` → `live_requires_token: false`.

## 4. Bobcoin caps: keep them

Removing the caps does not make the app more convincing, and it would let a single session eat the budget (it
happened: a large ZIP spent 5 bobcoins without finishing). With open access they matter even more. `render.yaml` sets:

| Variable | Value on Render | What it caps |
|---|---|---|
| `BOB_MAX_COST` | 3 | Bobcoins per audit, rescue turn included |
| `BOB_MAX_TURNS` | 30 | Orchestrator turns |
| `BOB_TIMEOUT_S` | 600 | Seconds per session |
| `MODERNIZE_PLAN_MAX_COST` | 1.5 | Studio assessment and plan |
| `MODERNIZE_STEP_MAX_COST` | 2 | Each implemented step |
| `MODERNIZE_TOTAL_MAX_COST` | 4 | A full implementation |
| `MODERNIZE_MAX_STEPS` | 5 | Steps per implementation |
| `BOB_DAILY_SPEND_LIMIT` | 15 | Bobcoins the server may spend per UTC day; then live features pause until the next day |

Fixed in code: `migration-architect` (1 bobcoin, 6 turns) and the chat (0.8 bobcoins, 12 turns). The server also runs
only **one** live audit and **one** Bob question at a time, and one Studio session with Bob at a time.

**Worst case per action:** live audit ≈ 4 bobcoins (3 + 1 from the architect); question ≈ 0.8; full Studio run ≈ 9
(1.5 + 1.5 + up to 6 in the implementation). The guard stops new Bob sessions after the process reaches 15 bobcoins
in one UTC day; it resets if the service restarts, so Daniel's IBM Bob account budget remains the hard ceiling. Adjust
`BOB_DAILY_SPEND_LIMIT` to the remaining budget and monitor it during judging. The home page shows
*Live spend today* next to the Bob status.

Real runs cost far less than the caps: between 0.57 and 1.44 bobcoins per FacturaYa audit and between 0.14 and 0.36
per question or step (see `docs/bob-usage.md`).

## 5. Variables on Render (summary)

| Variable | Value |
|---|---|
| `BOB_API_KEY` | Daniel's key (by hand, `sync: false`) |
| `LIVE_AUDIT_TOKEN` | **Not set** (open mode). Only as a kill switch |
| `BOB_ACCEPT_LICENSE` | `true` |
| `ENABLE_DEV_CORS` | `false` |
| Caps from section 4 | The ones in `render.yaml` |
| `ALLOW_NON_LIVE_MODES` | **Do not set it** (keeps the `example` mode off in production) |

## 6. Render's free plan

- **It sleeps after 15 minutes without traffic**: the first visit takes ~1 minute. During judging, set up a free
  monitor (e.g. UptimeRobot) that calls `GET /health` every 10 minutes, or move to the Starter plan while judging
  lasts.
- **Ephemeral disk**: every redeploy wipes the live analyses. The showcase rebuilds itself when opened.
- **512 MB of RAM**: the showcase fits easily. If a live audit fails for lack of memory, the showcase keeps working;
  the alternative is the Starter plan.
- **Do not merge into `main` during judging** except for urgent fixes: every merge redeploys and takes the URL down
  for a few minutes.
- **Home opens on the showcase:** the default tab is "FacturaYa · already generated", which spends no bobcoins.
  "Upload ZIP" is one click away (`frontend/src/views/ProjectsView.tsx`).

## 7. Smoke test before submitting

From an incognito window, with the public URL:

- [ ] `GET /health` answers `{"status":"ok"}`.
- [ ] `GET /api/bob/status` shows `installed` and `api_key_configured` as `true`, `live_requires_token` as `false`
      and `daily_spend_limit` as `15`.
- [ ] **FacturaYa · already generated → Open the FacturaYa analysis** opens the analysis with the `imported` label.
- [ ] The Bob session, the 12 findings with their cited code, the migration recommendation (`GET /invoices`) and the
      first cut with 6/6 tests all show up, in English.
- [ ] The DOCX memo downloads and opens.
- [ ] No token field appears anywhere.
- [ ] A short question to Bob gets an answer in English (spends < 1 bobcoin), and *Live spend today* goes up.
- [ ] The lablab.ai form has the URL and the repo link, and says live features spend capped bobcoins.
- [ ] No screenshot, video or text of the submission shows the API key.
