"""Similarity gate: decide which recalled memories the response actually 'used'.

Realizes state_updater's "reinforce memories actually used in the response" contract without LLM
attribution — a recalled memory is 'used' if its embedding is within ``threshold`` cosine of the
response embedding.
"""
from __future__ import annotations

from backend.layer2_memory.embedding import cosine_similarity


def used_memory_ids(response_embedding, scored_memories, threshold: float) -> set:
    used = set()
    if not response_embedding:
        return used
    for sm in scored_memories:
        mem = getattr(sm, "memory", None)
        emb = getattr(mem, "embedding", None) if mem is not None else None
        if emb and cosine_similarity(response_embedding, emb) >= threshold:
            used.add(mem.memory_id)
    return used
