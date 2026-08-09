"""Pattern detection job — Layer-10 behavioural-pattern sweep over persisted longitudinal data.

Runs weekly. Detects recurring patterns from persisted episodes + sessions, persists them (re-
identifying against last run's active patterns so has_been_surfaced/occurrence history survives
instead of duplicating every week -- same shape as Layer 5's social_pattern_job), and hands newly
active patterns off to Layer 6's outreach queue via the real on_behavioral_pattern intake contract.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")


def _pattern_key(p):
    """A stable identity for a pattern across runs -- the description's drifting numbers (avg
    valence, occurrence count) sit after a "(" or "--", so strip those before keying."""
    stable = p.description.split(" (")[0].split(" — ")[0]
    return (p.pattern_type, stable)


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from infra.db.proactive_store import PostgresProactiveQueue
    from backend.layer10_longitudinal.progress_tracker import detect_behavioral_patterns
    from backend.layer6_proactivity.intake import on_behavioral_pattern
    from background._adapters import emotional_records, episodic_records, session_records

    uid = app_state.default_user_id
    tz_offset = app_state.config.get("system", {}).get("timezone_offset_hours", 0.0)
    memory_store = PostgresMemoryStore(app_state.session_factory)
    eps = episodic_records(memory_store, uid, tz_offset)
    emos = emotional_records(memory_store, uid, tz_offset)
    sessions = session_records(app_state.session_factory, uid, tz_offset)
    patterns = detect_behavioral_patterns(emos, sessions, eps)

    store = PostgresLongitudinalStore(app_state.session_factory, uid)
    prior_by_key = {_pattern_key(p): p for p in store.active_patterns()}
    newly_active = []
    for pattern in patterns:
        prior = prior_by_key.pop(_pattern_key(pattern), None)
        if prior is None:
            newly_active.append(pattern)
        else:
            pattern.pattern_id = prior.pattern_id
    stale_ids = [p.pattern_id for p in prior_by_key.values()]
    store.save_patterns(patterns)
    store.deactivate_patterns(stale_ids)

    queue = PostgresProactiveQueue(app_state.session_factory, uid)
    for pattern in newly_active:
        item = on_behavioral_pattern(pattern)
        item.item_id = f"pattern-{pattern.pattern_id}"
        queue.upsert(item)

    logger.info("pattern detection: episodes=%d patterns=%d new=%d",
                len(eps), len(patterns), len(newly_active))
    return {"episodes": len(eps), "sessions": len(sessions), "patterns": len(patterns),
            "new_patterns": len(newly_active)}
