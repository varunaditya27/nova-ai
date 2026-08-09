"""Narrative arc job — Layer-10 SC-1 chapter synthesis over persisted longitudinal data.

Runs weekly. Rebuilds the user's NarrativeArc from persisted episodes and real, extracted
life events (`backend/layer10_longitudinal/life_event_extractor.py`, `api/state.py::
make_life_event_writer`) -- chapter-boundary detection can now actually fire, so a user who's
been through a real transition (new job, a move, a loss) gets a second chapter instead of one
ongoing chapter forever. Re-synthesizes the current chapter's narrative via an LLM, then persists
it so the per-turn read path (api/state.py::make_longitudinal_provider) has something real to
serve.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from backend.layer10_longitudinal.narrative_arc import build_narrative_arc
    from backend.layer10_longitudinal.life_narrative_engine import synthesize_chapter
    from background._adapters import emotional_records, episodic_records

    uid = app_state.default_user_id
    tz_offset = app_state.config.get("system", {}).get("timezone_offset_hours", 0.0)
    rel_store = PostgresRelationshipStore(app_state.session_factory, uid)
    arc_start = rel_store.first_session_date()
    if arc_start is None:
        return {"chapters": 0, "reason": "no relationship state yet"}

    memory_store = PostgresMemoryStore(app_state.session_factory)
    emos = emotional_records(memory_store, uid, tz_offset)
    eps = episodic_records(memory_store, uid, tz_offset)
    long_store = PostgresLongitudinalStore(app_state.session_factory, uid)
    life_events = long_store.life_events()

    arc = build_narrative_arc(uid, arc_start, life_events=life_events, emotional_records=emos)
    if arc.current_chapter is not None:
        client = (getattr(app_state, "llm_clients", None) or {}).get("system1")
        chapter_events = [e for e in life_events if e.event_id in arc.current_chapter.life_events]
        synthesize_chapter(
            arc.current_chapter, episodic_records=eps, life_events=chapter_events, goals=[],
            emotional_records=emos, llm_fn=(client.complete if client is not None else None))
        arc.narrative_version += 1

    long_store.save_narrative_arc(arc)
    logger.info("narrative arc: chapters=%d episodes=%d life_events=%d",
                len(arc.chapters), len(eps), len(life_events))
    return {"chapters": len(arc.chapters), "episodes": len(eps), "life_events": len(life_events)}
