# ChromaDB Vector Store
#
# Local persistent vector database for episodic, semantic, and identity memory retrieval.
#
# Components:
#   - chroma_client.py: PersistentClient wrapper
#   - collections.py: get_or_create_collection for each memory type
#   - embedding_fn.py: OllamaEmbeddingFunction (runs locally)
#
# No server required. All persistence is local to nova-data/chroma/.
