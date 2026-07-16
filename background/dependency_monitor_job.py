"""Dependency monitor job — Layer-11 SC-4 weekly check (architecture doc §6).

Runs weekly. Builds a deterministic, keyword-based indicator detector from the user's recent
episodic memories (no LLM - matches dependency_monitor.py's own "deterministic" design) and
computes the weighted dependency score. The real semantic-search-grade detector described in
the architecture doc (embeddings-based, not keyword-based) is a documented follow-up; this
keyword heuristic is a conservative first pass that keeps the job from always returning "no
signal" (its previous state: unreachable, since no job called it at all).

``previous_score`` (needed for the score's trend comparison) is not persisted across runs -
no existing store is shaped for arbitrary structured dependency-score storage without adding
a new table (PostgresSafetyLog is CrisisSignal-specific), so trend always reads "stable" for
now; wiring real cross-run persistence is a follow-up.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")

# A few observable keyword signals per indicator category - conservative, low-recall by design
# (false negatives are safe here; this only informs a graduated, never-announced intervention).
_KEYWORD_SIGNALS = {
    "SS_01": ("only one who understands", "only one i can talk to", "no one else gets me"),
    "SS_03": ("better than my friends", "better than my family", "don't need people"),
    "AE_04": ("don't need therapy", "don't need a therapist", "i'd rather just talk to you"),
    "EI_03": ("plan my life around", "wait until i can talk to you"),
}


def _build_indicator_detector(episode_summaries: list):
    text = " ".join(s.lower() for s in episode_summaries if s)

    def detector(indicator) -> bool:
        keywords = _KEYWORD_SIGNALS.get(indicator.indicator_id)
        if not keywords:
            return False
        return any(kw in text for kw in keywords)

    return detector


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer11_safety.dependency_monitor import compute_dependency_score

    uid = app_state.default_user_id
    store = PostgresMemoryStore(app_state.session_factory)
    episodes = store.active_episodic(uid)
    detector = _build_indicator_detector([getattr(e, "summary", "") for e in episodes])

    result = compute_dependency_score(uid, indicator_detector=detector)
    logger.info("dependency check: user=%s tier=%s score=%.2f", uid, result.tier, result.score)
    return {
        "tier": result.tier, "score": result.score, "trend": result.trend,
        "dominant_signals": result.dominant_signals,
    }
