"""Vector store infrastructure — ChromaDB service client + Ollama embedding function.

`ChromaVectorStore` / `build_vector_store` are imported lazily (PEP 562) so that importing this
package — or the pure `embedding_fn` submodule — never pulls in `chromadb`. That keeps the offline
unit suite collectable on a base (pure-stdlib) install where the `infra` extra isn't present.
"""
from __future__ import annotations

from infra.vector_store.collections import COLLECTIONS
from infra.vector_store.embedding_fn import OllamaEmbeddingFunction

__all__ = ["ChromaVectorStore", "COLLECTIONS", "OllamaEmbeddingFunction", "build_vector_store"]


def __getattr__(name: str):
    if name in ("ChromaVectorStore", "build_vector_store"):
        from infra.vector_store.chroma_client import ChromaVectorStore

        if name == "ChromaVectorStore":
            return ChromaVectorStore

        def build_vector_store(config: dict) -> ChromaVectorStore:
            sysc = config["system"]
            return ChromaVectorStore(host=sysc["chroma_host"], port=sysc["chroma_port"])

        return build_vector_store
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
