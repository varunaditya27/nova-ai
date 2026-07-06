"""Memory consolidation job — Layer-2 forgetting sweep over persisted episodes.

Runs every ~2h. Recomputes each active episode's decayed strength and archives/deletes the ones
that fall below threshold (``decay_sweep``), then persists the results. Deterministic; no LLM.
(Cluster detection → semantic extraction is a heavier follow-up; the decay sweep is the core.)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer2_memory.forgetting_engine import decay_sweep

    uid = app_state.default_user_id
    store = PostgresMemoryStore(app_state.session_factory)
    episodes = [e for e in store.all_episodic(uid) if not getattr(e, "is_deleted", False)]
    deleted, archived = decay_sweep(episodes, datetime.now(timezone.utc))
    for ep in episodes:
        store.save_episodic(ep)
    logger.info("consolidation: swept=%d deleted=%d archived=%d", len(episodes), deleted, archived)
    return {"swept": len(episodes), "deleted": deleted, "archived": archived}
