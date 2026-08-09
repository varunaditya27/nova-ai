"""Post-distress gap check — Layer 6 SC-1 intake ``on_post_distress_gap`` (architecture doc §9.2).

Runs daily. ``on_post_distress_gap`` had zero production callers: it needed a "user had a
high-distress session, then went quiet for days" signal, which PENDING_WORK.md flagged as
"blocked on a Layer 2 state-updater hook that doesn't exist yet." Re-investigated: no new hook is
actually needed -- the real, already-persisted episodic memories already carry `emotion_vector`
(the same real signal Layer 10/11's jobs already reuse via `background._adapters`), so the most
recent high-distress episode and the real gap since it are both directly derivable from
``memory_store.active_episodic``, matching the pattern `dependency_monitor_job.py` already uses.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("nova.jobs")

_DISTRESS_VALENCE_FLOOR = -0.6


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from infra.db.proactive_store import PostgresProactiveQueue
    from backend.layer6_proactivity.intake import on_post_distress_gap

    uid = app_state.default_user_id
    now = datetime.now(timezone.utc)
    store = PostgresMemoryStore(app_state.session_factory)
    episodes = store.active_episodic(uid)

    distressed = [
        ep for ep in episodes
        if float(getattr(getattr(ep, "emotion_vector", None), "valence", 0.0) or 0.0)
        < _DISTRESS_VALENCE_FLOOR
        and getattr(ep, "created_at", None) is not None
    ]
    if not distressed:
        return {"episodes_scanned": len(episodes), "queued": False}

    latest = max(distressed, key=lambda e: e.created_at)
    created_at = latest.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    gap_days = (now - created_at).days
    valence = float(latest.emotion_vector.valence)

    item = on_post_distress_gap(
        session_summary=getattr(latest, "summary", "") or "",
        episode_id=str(getattr(latest, "memory_id", "")),
        end_valence=valence, gap_days=gap_days, now=now)
    if item is None:
        return {"episodes_scanned": len(episodes), "queued": False, "gap_days": gap_days}

    item.item_id = f"distressgap-{getattr(latest, 'memory_id', '')}"
    PostgresProactiveQueue(app_state.session_factory, uid).upsert(item)
    logger.info("post-distress gap: user=%s gap_days=%d valence=%.2f queued", uid, gap_days, valence)
    return {"episodes_scanned": len(episodes), "queued": True, "gap_days": gap_days}
