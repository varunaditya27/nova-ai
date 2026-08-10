#!/usr/bin/env bash
# Run the full Nova AI backend live on the local host. The platform runs fully offline against
# Ollama by default (config/defaults.yaml) — no cloud provider, no API key.
#
# Points every backend at the loopback-published container ports, applies migrations, then serves
# the API. Requires: docker services up (postgres, chroma, ollama) and the models pulled
# (qwen2.5:7b, gemma2:2b, nomic-embed-text — or your own via NOVA_MAIN_MODEL/NOVA_MINI_MODEL).
set -euo pipefail
cd "$(dirname "$0")/.."

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://nova:nova@127.0.0.1:5432/nova}"
export NOVA_DATABASE_URL="${NOVA_DATABASE_URL:-$DATABASE_URL}"   # alembic env reads this
export CHROMA_HOST="${CHROMA_HOST:-127.0.0.1}"
export CHROMA_PORT="${CHROMA_PORT:-8001}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export KOKORO_URL="${KOKORO_URL:-http://127.0.0.1:8880}"
export NOVA_USER_ID="${NOVA_USER_ID:-local-user}"

PY="${PY:-.venv/bin/python}"

echo "→ applying migrations (alembic upgrade head)"
"$PY" -m alembic upgrade head

echo "→ starting API on http://127.0.0.1:8000 (fully offline, local Ollama)"
exec "$PY" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
