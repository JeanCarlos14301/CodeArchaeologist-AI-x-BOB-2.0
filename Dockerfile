# syntax=docker/dockerfile:1
# Contenedor único (D11): FastAPI (API + worker) + Bob Shell + build estático de React.
# Local:   docker compose up --build   → http://127.0.0.1:8000
# Render:  ver render.yaml y docs/deploy.md

# --- Etapa 1: build del frontend ---------------------------------------------------------
FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Etapa 2: Node 24 para Bob Shell (solo se copian sus binarios) -----------------------
FROM node:24-bookworm-slim AS node

# --- Etapa 3: runtime ---------------------------------------------------------------------
FROM python:3.11-slim-bookworm

# Versión probada por el equipo; el checksum sale de bob-shell/bobshell-<versión>.tgz.sha256.
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

# Bob Shell: mismo paquete que instala bobshell.sh, pero fijado y con checksum verificado.
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

# Mismo layout que el repo: REPO_ROOT (bob_adapter.py) resuelve a /app.
COPY .bob .bob
COPY backend backend
COPY contracts contracts
COPY samples samples
COPY --from=frontend /build/dist frontend/dist

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/artifacts \
    && chown app:app /app/artifacts
USER app

# DATABASE_PATH: la base del motor de 11 etapas debe vivir en el único directorio escribible.
# ENABLE_JOBS_API=false: /api/jobs acepta ZIP arbitrarios y lanza Bob sin token ni tope de
# coste; queda apagado en público hasta que aplique las mismas protecciones que /api/audits.
# PYTHONPATH=/app: parte del backend se importa como `backend.app.*` (raíz del repo) y otra
# como `app.*` (--app-dir backend en el CMD); ambos deben resolverse.
ENV PYTHONPATH=/app \
    ARTIFACTS_DIR=/app/artifacts \
    DATABASE_PATH=/app/artifacts/pipeline.db \
    ENABLE_DEV_CORS=false \
    ENABLE_JOBS_API=false \
    PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# Render inyecta PORT; en local queda 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
