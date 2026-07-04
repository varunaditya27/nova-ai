"""Vector store infrastructure — ChromaDB service client + Ollama embedding function."""
from __future__ import annotations

from infra.vector_store.chroma_client import ChromaVectorStore
from infra.vector_store.collections import COLLECTIONS
from infra.vector_store.embedding_fn import OllamaEmbeddingFunction

__all__ = ["ChromaVectorStore", "COLLECTIONS", "OllamaEmbeddingFunction", "build_vector_store"]


def build_vector_store(config: dict) -> ChromaVectorStore:
    sysc = config["system"]
    return ChromaVectorStore(host=sysc["chroma_host"], port=sysc["chroma_port"])
