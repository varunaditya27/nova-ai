"""Memory consolidation job — Layer-2 forgetting sweep + FCE semantic extraction over persisted
episodes.

Runs every ~2h. Recomputes each active episode's decayed strength and archives/deletes the ones
that fall below threshold (``decay_sweep``), then persists the results (always). When enough
active episodes have accumulated (``EPISODE_COUNT_TRIGGER``), also runs agglomerative cluster
detection over them and compresses each qualifying cluster into a semantic memory via an
injected LLM generalizer (``app_state.llm_clients["system1"]``), persisting both the new semantic
memory and the now-consolidated episodes.

``should_trigger_fce``'s ``sessions_since``/``days_since`` OR-conditions need a persisted
"since last run" counter this job does not keep (no new table); only the episode-count
condition is checked directly here — the other two trigger paths are a documented follow-up.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer2_memory.forgetting_engine import (
        EPISODE_COUNT_TRIGGER, cluster_detection, decay_sweep, extract_semantic_memory,
    )

    uid = app_state.default_user_id
    store = PostgresMemoryStore(app_state.session_factory)
    now = datetime.now(timezone.utc)

    episodes = [e for e in store.all_episodic(uid) if not getattr(e, "is_deleted", False)]
    deleted, archived = decay_sweep(episodes, now)
    for ep in episodes:
        store.save_episodic(ep)

    clusters_detected = semantic_memories_created = episodes_consolidated = 0
    new_summaries: list[str] = []

    active = [e for e in episodes if not e.is_deleted]
    if len(active) >= EPISODE_COUNT_TRIGGER:
        clusters = cluster_detection(active)
        clusters_detected = len(clusters)

        def _generalize(summaries: list[str]) -> str:
            client = (getattr(app_state, "llm_clients", None) or {}).get("system1")
            if client is None:
                return summaries[0] if summaries else ""
            prompt = ("Summarize the common pattern across these journal-like notes into one "
                      "short third-person statement about the user: " + " | ".join(summaries))
            try:
                return client.complete(prompt).strip()
            except Exception:
                return summaries[0] if summaries else ""

        for cluster in clusters:
            semantic = extract_semantic_memory(cluster, uid, _generalize, now)
            store.save_semantic(semantic)
            for ep in cluster.members:
                store.save_episodic(ep)  # persist consolidated_into / is_deleted from extraction
            semantic_memories_created += 1
            episodes_consolidated += len(cluster.members)
            new_summaries.append(semantic.statement)

    logger.info("consolidation: swept=%d deleted=%d archived=%d clusters=%d semantic=%d",
                len(episodes), deleted, archived, clusters_detected, semantic_memories_created)
    return {
        "swept": len(episodes), "deleted": deleted, "archived": archived,
        "clusters_detected": clusters_detected,
        "semantic_memories_created": semantic_memories_created,
        "episodes_consolidated": episodes_consolidated,
        "new_semantic_summaries": new_summaries,
    }
