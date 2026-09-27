# Deployment

A single container (D11) built from the `Dockerfile` and deployed on **Render**. Every push to `main` triggers CI
(`.github/workflows/ci.yml`); if it passes, Render rebuilds and publishes the same URL
(`render.yaml` → `autoDeployTrigger: checksPass`).

```
push to main ──► CI: pytest + frontend build + image build and smoke test
                     │ passes
                     ▼
                Render rebuilds the Dockerfile ──► public URL
```

## First deployment

1. Sign in to <https://dashboard.render.com> with a GitHub account that has access to the repository.
2. **New → Blueprint** and pick the repository. Render reads `render.yaml` and proposes the `codearchaeologist`
   service (Docker runtime).
3. When it asks for `BOB_API_KEY`, paste a Bob API key (*Inference* scope). It is stored only in Render, never in the
   repository ([SECURITY.md](../SECURITY.md)).
4. **Apply**. The first build takes several minutes (it installs Python, Node 24 and Bob Shell).

## Access: open mode with a kill switch

The blueprint does not define `LIVE_AUDIT_TOKEN`, so the app runs in **open mode** (D40): anyone can open the
showcase, upload a ZIP, ask Bob and use the Studio with no token. Uploaded analyses are never listed publicly; they
are reachable only through their random job id.

**Kill switch:** if someone abuses the public URL, add `LIVE_AUDIT_TOKEN` with a long random value in Render →
**Environment** (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). About a minute later every Bob call
and every read of an upload requires the token, and the interface shows the token fields. The showcase keeps
working. Remove the variable to reopen.

## Bobcoin caps

`render.yaml` sets these limits so a single session cannot drain the budget:

| Variable | Value | What it caps |
|---|---|---|
| `BOB_MAX_COST` | 3 | Bobcoins per audit, rescue turn included |
| `BOB_MAX_TURNS` | 30 | Orchestrator turns |
| `BOB_TIMEOUT_S` | 600 | Seconds per session |
| `MODERNIZE_PLAN_MAX_COST` | 1.5 | Studio assessment and plan |
| `MODERNIZE_STEP_MAX_COST` | 2 | Each implemented step |
| `MODERNIZE_TOTAL_MAX_COST` | 4 | A full implementation |
| `MODERNIZE_MAX_STEPS` | 5 | Steps per implementation |
| `BOB_DAILY_SPEND_LIMIT` | 15 | Bobcoins per UTC day; then live features pause until the next day |

Fixed in code: `migration-architect` (1 bobcoin, 6 turns) and the chat (0.8 bobcoins, 12 turns). The server runs only
one live audit, one Bob question and one Studio session at a time. Real runs cost far less than the caps: between
0.57 and 1.44 bobcoins per FacturaYa audit and between 0.14 and 0.36 per question or step
([docs/bob-usage.md](bob-usage.md)).

Keep `ALLOW_NON_LIVE_MODES` unset in production so the `example` mode stays off.

## Check a deployment

```bash
curl https://<your-service>.onrender.com/health          # {"status":"ok"}
curl https://<your-service>.onrender.com/api/bob/status  # installed and api_key_configured true; live_requires_token false
```

## Locally, the same as on Render

```bash
docker compose up --build        # http://127.0.0.1:8000, reads .env if it exists
```

Without `LIVE_AUDIT_TOKEN` in `.env`, the server runs in open mode; with it, locked mode.

## Free plan limits

- **It sleeps after 15 min without traffic**: the first visit takes about a minute. An uptime monitor that calls
  `GET /health` every 10 minutes keeps it awake.
- **512 MB of RAM**: the imported showcase fits easily. A live audit launches Bob Shell inside the container; if it
  fails for lack of memory, use a paid plan.
- **Ephemeral disk**: the job history (`artifacts/`) is wiped on every deploy or restart. The imported showcase is
  always available.

## If something goes wrong

- **Undo a deployment**: Render → *Deploys* → *Rollback* on the last one that worked, or `git revert` the commit and
  push to `main`.
- **`A license agreement is required`**: `BOB_ACCEPT_LICENSE=true` is missing in Environment.
- **`BOB_API_KEY is missing from the environment`**: the variable is empty in Environment.
- **The build fails in CI**: Render does not deploy; the URL keeps serving the previous version.
