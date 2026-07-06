"""ANN-backed recall candidate source (Layer-2 live vector path).

Wraps a PostgresMemoryStore for one recall: ``candidate_memories`` asks ChromaDB for the query's
nearest episodic neighbours (ANN) and hydrates them from Postgres, instead of linearly scanning
every episode. Everything else delegates to the base store. Bound to one query embedding + user.

Degrades safely: if the vector store errors or the index is cold (no hits), it falls back to the
base store's linear ``candidate_memories`` — so offline tests with a mock/absent vector store, and a
freshly-seeded DB whose embeddings are not yet indexed, both still recall.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.recall")

_EPISODIC = "episodic"


class AnnRecallStore:
    def __init__(self, base, vector_store, query_embedding, user_id, k: int = 20) -> None:
        self._base = base
        self._vs = vector_store
        self._q = query_embedding
        self._uid = str(user_id)
        self._k = k

    def candidate_memories(self, user_id):
        try:
            hits = self._vs.query(_EPISODIC, self._q, n_results=self._k,
                                  where={"user_id": self._uid})
            ids = [h["id"] for h in hits if h.get("id")]
        except Exception:
            logger.exception("ANN query failed; falling back to linear candidate scan")
            return self._base.candidate_memories(user_id)
        if not ids:
            return self._base.candidate_memories(user_id)   # cold index → linear fallback

        episodic = []
        for mid in ids:
            ep = self._base.get_episodic(mid)
            if ep is not None and not getattr(ep, "is_deleted", False):
                episodic.append(ep)
        # Semantic memories are not ANN-indexed here; keep them in the candidate set as before.
        try:
            semantic = self._base.active_semantic(self._uid)
        except Exception:
            semantic = []
        return [*episodic, *semantic]

    def __getattr__(self, name):
        # Delegate every other store method (get_episodic, active_semantic, load_uwm, query_uwm, …).
        return getattr(self._base, name)
