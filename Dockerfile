# syntax=docker/dockerfile:1
# Single container (D11): FastAPI (API + worker) + Bob Shell + static React build.
# Local:   docker compose up --build   → http://127.0.0.1:8000
# Render:  see render.yaml and docs/deploy.md

# --- Stage 1: frontend build ------------------------------------------------------------
FROM node:24-bookworm-slim AS frontend
# Mirror the repo layout: src/fixtures/index.ts imports ../../../contracts/fixtures/*.json,
# so the contract fixtures must sit next to frontend/ exactly as they do in the repo.
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY contracts/fixtures /build/contracts/fixtures
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Node 24 for Bob Shell (only its binaries are copied) ----------------------
FROM node:24-bookworm-slim AS node

# --- Stage 3: runtime ------------------------------------------------------------------
FROM python:3.11-slim-bookworm

# Version tested by the team; the checksum comes from bob-shell/bobshell-<version>.tgz.sha256.
ARG BOB_VERSION=2.0.5
ARG BOB_SHA256=eff232eb1b69f34f984ddd295e6960470058ca922b1c751879c5a8d06199f566

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Bob Shell: the same package bobshell.sh installs, but pinned and with a verified checksum.
RUN curl -fsSL -o /tmp/bobshell.tgz \
        "https://s3.us-south.cloud-object-storage.appdomain.cloud/bob-shell/bobshell-${BOB_VERSION}.tgz" \
    && echo "${BOB_SHA256}  /tmp/bobshell.tgz" | sha256sum -c - \
    && npm install -g --registry=https://registry.npmjs.org/ --allow-scripts=@officecli/officecli \
        --progress=false --loglevel=error /tmp/bobshell.tgz \
    && rm /tmp/bobshell.tgz \
    && npm cache clean --force \
    && bob --version

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# Same layout as the repo: REPO_ROOT (bob_adapter.py) resolves to /app.
COPY .bob .bob
COPY backend backend
COPY contracts contracts
COPY samples samples
COPY --from=frontend /build/frontend/dist frontend/dist

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/artifacts \
    && chown app:app /app/artifacts
USER app

# DATABASE_PATH: the pipeline database must live in the only writable directory.
# PYTHONPATH=/app: part of the backend is imported as `backend.app.*` (repo root) and part
# as `app.*` (--app-dir backend in the CMD); both must resolve.
ENV PYTHONPATH=/app \
    ARTIFACTS_DIR=/app/artifacts \
    DATABASE_PATH=/app/artifacts/pipeline.db \
    ENABLE_DEV_CORS=false \
    PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# Render injects PORT; locally it stays 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
