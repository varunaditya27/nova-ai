"""Canonical Chroma collections for Layer 2 memory embeddings (cosine space)."""

_COSINE = {"hnsw:space": "cosine"}

COLLECTIONS = {
    "episodic": {"name": "episodic_memory", "metadata": _COSINE},
    "semantic": {"name": "semantic_memory", "metadata": _COSINE},
    "identity": {"name": "identity_memory", "metadata": _COSINE},
}
