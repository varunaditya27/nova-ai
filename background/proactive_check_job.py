"""Proactive check job — maintain the Layer-6 outreach queue.

Runs every ~30 min. Loads the persisted queue, recomputes priorities, expires stale items, and
persists the results. Message generation/delivery needs a delivery channel (a client polls
``GET /proactive`` for the top candidates), so this job owns the deterministic queue maintenance.
Suppressed for a cold-starting user (Layer-13 keeps proactivity observe-only).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.proactive_store import PostgresProactiveQueue
    from infra.db.onboarding_store import PostgresOnboardingStore
    from backend.layer6_proactivity.queue_manager import ProactiveQueueManager

    uid = app_state.default_user_id
    grad = (getattr(app_state, "config", {}) or {}).get("onboarding", {}).get("graduation_sessions", 5)
    if PostgresOnboardingStore(app_state.session_factory, uid, grad).state().get("cold_start_active"):
        return {"skipped": "cold_start_active"}

    q = PostgresProactiveQueue(app_state.session_factory, uid)
    items = q.load()
    mgr = ProactiveQueueManager(items)
    now = datetime.now(timezone.utc)
    try:
        mgr.recompute_all(bes_trend="stable", now=now, session_gap_days=0.0)
    except Exception:  # priority recompute needs per-item windows; never block expiry/persist
        logger.exception("proactive recompute failed; continuing with expiry + persist")
    expired = mgr.expire(now)
    q.save_all(mgr.items)
    return {"queued": len(mgr.items), "expired": len(expired),
            "top": [i.item_id for i in mgr.top_candidates(3)]}
