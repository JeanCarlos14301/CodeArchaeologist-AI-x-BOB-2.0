# Deployment (J-02 / J-03)

A single container (D11) built from the `Dockerfile` and deployed on **Render**. Every push to
`main` triggers CI (`.github/workflows/ci.yml`); if it passes, Render rebuilds and publishes the
same URL (`render.yaml` → `autoDeployTrigger: checksPass`).

```
push to main ──► CI: pytest + frontend build + image build and smoke test
                     │ passes
                     ▼
                Render rebuilds the Dockerfile ──► https://<service>.onrender.com
```

## First time (≈10 min, done once by Jean)

1. Merge the approved branches into `main`; Render deploys only from `main`.
2. Sign in to <https://dashboard.render.com> with the GitHub account that has access to the repo.
3. **New → Blueprint**, pick the repo. Render reads `render.yaml` and proposes the
   `codearchaeologist` service (free plan, Docker runtime).
4. When it asks for `BOB_API_KEY`, paste the Bob API key (*Inference* scope). It is stored only in
   Render, never in the repo (SECURITY.md).
5. **Apply**. The first build takes several minutes (it installs Python, Node 24 and Bob Shell).
6. Access mode: the blueprint does not define `LIVE_AUDIT_TOKEN`, so the app runs in **open mode** and the judges
   need no token (D40). If an earlier blueprint created `LIVE_AUDIT_TOKEN`, delete it in **Environment**: removing a
   variable from `render.yaml` does not delete it from an existing service. How the app is published:
   `docs/submission/public-app.md`.
7. Recommended: in GitHub → *Settings → Branches*, protect `main` by requiring the `backend`, `frontend` and
   `docker` CI checks. That way nobody breaks the public URL with a direct push.

## Check a deployment

```bash
curl https://<service>.onrender.com/health          # {"status":"ok"}
curl https://<service>.onrender.com/api/bob/status  # installed and api_key_configured true; live_requires_token false (open mode)
```

In the interface, the FacturaYa showcase (imported) works for anyone and spends no bobcoins. Live audits, ZIP
uploads, Ask Bob and the Modernization Studio call Bob for real and spend bobcoins from the configured account,
within the caps in `render.yaml`. The `example` mode is off unless `ALLOW_NON_LIVE_MODES=true`.

## Kill switch

If someone abuses the public URL, add `LIVE_AUDIT_TOKEN` with a long random value in Render → **Environment** and
save. Render restarts the service in about a minute; from then on every Bob call and every read of an upload
requires the token, and the interface shows the token fields. The showcase keeps working without a token.

## Locally, the same as on Render

```bash
docker compose up --build        # http://127.0.0.1:8000, reads .env if it exists
```

Without `LIVE_AUDIT_TOKEN` in `.env`, the server runs in open mode; with it, locked mode.

## Free plan limits

- **It sleeps after 15 min without traffic**: the first visit takes ~1 min. Open the URL a couple of minutes before
  recording the video or before the judges try it, or keep it awake with an uptime monitor (see
  `docs/submission/public-app.md`).
- **512 MB of RAM**: the imported showcase fits easily. A **live** audit launches Bob Shell inside the container; if
  it fails for lack of memory, the options are a paid Render plan or recording the live part from a PC (plan B of
  D11/D12).
- **Ephemeral disk**: the job history (`artifacts/`) is wiped on every deploy or restart. For the demo it does not
  matter: the imported showcase is always available.

## If something goes wrong

- **Undo a deployment**: Render → *Deploys* → *Rollback* on the last one that worked, or `git revert` the commit and
  push to `main`.
- **`A license agreement is required`**: `BOB_ACCEPT_LICENSE=true` is missing in Environment.
- **`BOB_API_KEY is missing from the environment`**: the variable is empty in Environment.
- **The build fails in CI**: Render does not deploy; the URL keeps serving the previous version.
