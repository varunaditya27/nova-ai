# Chroma Collections
#
# Responsibility: Initialize and manage the three main collections.
#
# Collections:
#   - episodic: Episodic memories (sessions, events, etc.)
#   - semantic: Semantic facts about the user
#   - identity: Identity/belief memories
#
# Each collection has:
#   - Name (string identifier)
#   - Metadata schema (what fields can be filtered on)
#   - Embedding space (via OllamaEmbeddingFunction)
#
# Main functions:
#   - get_or_create_collection(collection_name) -> Collection
#   - initialize_all_collections() -> None
