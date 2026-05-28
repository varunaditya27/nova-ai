# Chroma Client
#
# Responsibility: Manage ChromaDB PersistentClient instance.
#
# Main function:
#   - get_chroma_client() -> PersistentClient
#   - initialize_collections() -> None
#
# Configuration:
#   - CHROMA_PERSIST_PATH: Path to persistent storage (default: ./nova-data/chroma/)
#   - Connected to Ollama for embeddings (localhost:11434)
