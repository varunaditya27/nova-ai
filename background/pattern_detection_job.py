"""Pattern detection job — Layer-10 behavioural-pattern sweep over persisted longitudinal data.

Runs weekly. Detects recurring patterns from persisted episodes + sessions. Detected patterns are
returned (a follow-up feeds high-confidence patterns into the Layer-6 proactive queue).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer10_longitudinal.progress_tracker import detect_behavioral_patterns
    from background._adapters import emotional_records, episodic_records, session_records

    uid = app_state.default_user_id
    store = PostgresMemoryStore(app_state.session_factory)
    eps = episodic_records(store, uid)
    emos = emotional_records(store, uid)
    sessions = session_records(app_state.session_factory, uid)
    patterns = detect_behavioral_patterns(emos, sessions, eps)
    logger.info("pattern detection: episodes=%d patterns=%d", len(eps), len(patterns))
    return {"episodes": len(eps), "sessions": len(sessions), "patterns": len(patterns)}
