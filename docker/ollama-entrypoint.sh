#!/usr/bin/env bash
# Start the Ollama server, then pull the models Nova needs on first boot.
# Models are cached in the mounted volume, so subsequent starts are fast.
set -euo pipefail

ollama serve &
server_pid=$!

# Wait for the API to accept requests before pulling.
until ollama list >/dev/null 2>&1; do
  sleep 1
done

for model in qwen2.5:7b gemma2:2b nomic-embed-text; do
  echo "[ollama-entrypoint] pulling ${model}..."
  ollama pull "${model}" || echo "[ollama-entrypoint] WARN: failed to pull ${model}"
done

echo "[ollama-entrypoint] models ready; server running."
wait "${server_pid}"
