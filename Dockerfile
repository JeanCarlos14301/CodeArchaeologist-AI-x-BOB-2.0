# Placeholder — J-02 (Jean, H0–H3).
# Un solo contenedor: FastAPI (API + worker) + Bob Shell + build estático de React.
#
# TODO: etapa 1 — build del frontend con Node 24
#   FROM node:24-slim AS frontend
#   ... npm ci && npm run build (frontend/ -> dist/)
#
# TODO: etapa 2 — runtime con Python 3.11
#   FROM python:3.11-slim
#   ... instalar Node 24 (requerido por Bob Shell)
#   ... instalar Bob Shell
#   ... pip install -r backend/requirements.txt
#   ... copiar backend/ y el dist/ del frontend
#   ... usuario no root, EXPOSE, HEALTHCHECK contra /health
#   ... CMD uvicorn app.main:app
