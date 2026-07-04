# Ollama local inference image — serves System 1 (qwen2.5:7b), a classifier fallback
# (gemma3:4b), and embeddings (nomic-embed-text). Models are pulled on first start by
# the entrypoint and cached in the ollama volume (not baked into the image).
# Build context is the repo root (compose sets context: ..).
FROM ollama/ollama:latest

COPY docker/ollama-entrypoint.sh /usr/local/bin/ollama-entrypoint.sh
RUN chmod +x /usr/local/bin/ollama-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/ollama-entrypoint.sh"]
