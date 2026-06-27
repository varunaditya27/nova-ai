"""Embedding utilities for Layer 2 (architecture doc §4.4, §8.2, §17.1).

Production uses all-MiniLM-L6-v2 (384-dim) for vectors and hnswlib (in-process, on-device,
no server) for the index. Both sit behind ``Embedder`` / ``VectorIndex`` protocols so the
deterministic, dependency-free implementations here drive tests and offline development, and
the real backends drop in without touching the memory engine.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [-1, 1]; 0.0 if either vector is zero-length or all-zeros."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    # Clamp to guard against floating-point drift slightly outside [-1, 1].
    return max(-1.0, min(1.0, dot / (na * nb)))


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class DeterministicEmbedder:
    """A hashing embedder: deterministic, offline, no model.

    Tokens are hashed into a fixed-dimensional bag-of-words vector, then L2-normalized.
    Good enough for similarity ordering in tests/dev; the real semantic model implements the
    same ``embed`` signature.
    """

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = (text or "").lower().split()
        for tok in tokens:
            h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return vec
        return [x / norm for x in vec]


class VectorIndex(Protocol):
    def add(self, key: str, embedding: list[float]) -> None: ...
    def search(self, query: list[float], top_k: int) -> list[tuple[str, float]]: ...


class BruteForceVectorIndex:
    """In-process exact cosine search. Stand-in for hnswlib; identical interface."""

    def __init__(self) -> None:
        self._items: list[tuple[str, list[float]]] = []

    def add(self, key: str, embedding: list[float]) -> None:
        self._items.append((key, list(embedding)))

    def search(self, query: list[float], top_k: int) -> list[tuple[str, float]]:
        scored = [(key, cosine_similarity(query, emb)) for key, emb in self._items]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:top_k]
