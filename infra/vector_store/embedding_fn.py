"""Chroma-compatible embedding function backed by an LLMClient (Ollama nomic-embed-text)."""
from __future__ import annotations


class OllamaEmbeddingFunction:
    """Implements Chroma's EmbeddingFunction protocol: __call__(input) -> embeddings."""

    def __init__(self, client):
        self._client = client

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002 (Chroma's arg name)
        return self._client.embed(list(input))

    def name(self) -> str:
        return "ollama-embedding-function"
