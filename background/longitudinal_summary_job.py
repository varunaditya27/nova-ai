"""Longitudinal summary job — generate + persist a Layer-10 weekly summary.

Runs weekly. Assembles the past week's summary from persisted sessions + episodes (mapped to the
Layer-10 record shapes) and saves it via PostgresLongitudinalStore, so ``GET /longitudinal/*`` can
serve it. LLM narrative is optional (offline → deterministic aggregation only).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer10_longitudinal.weekly_summary import generate_weekly_summary
    from background._adapters import emotional_records, episodic_records, session_records

    uid = app_state.default_user_id
    store = PostgresMemoryStore(app_state.session_factory)
    eps = episodic_records(store, uid)
    emos = emotional_records(store, uid)
    sessions = session_records(app_state.session_factory, uid)

    now = datetime.now(timezone.utc)
    week_end = now.date()
    week_start = week_end - timedelta(days=7)
    summary = generate_weekly_summary(uid, week_start, week_end, eps, emos, sessions, now=now)

    PostgresLongitudinalStore(app_state.session_factory, uid).save_summary(summary, period="weekly")
    logger.info("longitudinal: summary=%s sessions=%d episodes=%d",
                summary.summary_id, len(sessions), len(eps))
    return {"summary_id": summary.summary_id, "sessions": len(sessions), "episodes": len(eps)}
