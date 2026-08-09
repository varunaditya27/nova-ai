"""Proactive check job — maintain the Layer-6 outreach queue.

Runs every ~30 min. Loads the persisted queue, recomputes priorities, expires stale items,
generates the real SC-4 delivery message for items that clear the SC-3 timing gate right now
(2026-08-09 — this job already runs every ~30 min and already calls ``save_all``, so it's the
natural place for the LLM call an HTTP read endpoint like ``GET /proactive`` must never make),
and persists the results. Suppressed for a cold-starting user (Layer-13 keeps proactivity
observe-only).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.proactive_store import PostgresProactiveQueue
    from infra.db.onboarding_store import PostgresOnboardingStore
    from backend.layer6_proactivity.queue_manager import ProactiveQueueManager
    from api.proactive_delivery import build_timing_context, gate_passes, generate_message_for_item

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

    generated = 0
    try:
        ctx = build_timing_context(app_state.session_factory, uid, now, app_state.config)
        for item in mgr.items:
            if item.generated_message or item.status not in ("pending", "deferred"):
                continue
            if not gate_passes(item, ctx, now):
                continue
            try:
                text = generate_message_for_item(app_state, item, uid, now)
            except Exception:
                logger.exception("SC-4 message generation failed for item %s", item.item_id)
                continue
            if text:
                item.generated_message = text
                generated += 1
    except Exception:  # never block expiry/persist on generation trouble
        logger.exception("proactive message generation pass failed; continuing with persist")

    q.save_all(mgr.items)
    return {"queued": len(mgr.items), "expired": len(expired), "generated": generated,
            "top": [i.item_id for i in mgr.top_candidates(3)]}
