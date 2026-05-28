# Ollama Embedding Function
#
# Responsibility: Provide embeddings via Ollama's local API.
#
# Model:
#   - nomic-embed-text (free, runs locally, fast)
#   - Pulled from Ollama on startup
#
# Main functions:
#   - embed_query(query: str) -> list[float]
#   - embed_documents(documents: list[str]) -> list[list[float]]
#
# Configuration:
#   - OLLAMA_EMBED_MODEL: Model name (default: nomic-embed-text)
#   - OLLAMA_EMBED_URL: Ollama API endpoint (default: http://localhost:11434)
