"""Social pattern detection job — Layer-5 SC-3 batch sweep over the persisted SocialGraph.

Runs weekly (architecture doc §5.4 specifies "every 5 sessions"; no session-since-last-run
counter exists anywhere in this codebase yet -- see docs/POLISH_BACKLOG.md -- so this uses the
same fixed-interval shape every other job in background/scheduler.py already uses). Detects
recurring social patterns from the persisted event history and upserts them; detected patterns
become visible to the live coaching-injection hook (api/assembly.py::social_coaching) the next
time it runs, via the same PostgresSocialStore.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.social_store import PostgresSocialStore
    from backend.layer5_relationship import detect_patterns

    uid = app_state.default_user_id
    store = PostgresSocialStore(app_state.session_factory)
    graph = store.load_graph(uid)
    if graph is None:
        return {"nodes": 0, "events": 0, "patterns": 0}
    events = store.recent_events(uid)
    # Explicit tz-aware `now`: detect_patterns' own default is naive (`datetime.utcnow()`), but
    # real SocialEvent.reported_timestamp is stamped tz-aware (make_social_writer uses
    # datetime.now(timezone.utc)) -- same class of bug caught and fixed the same way in Layer 3's
    # BES wiring (docs/layer-3-architecture.md §18): comparing the two raises, and the exception
    # would silently abort this job every single run against any real data.
    patterns = detect_patterns(graph, events, now=datetime.now(timezone.utc))

    # detect_patterns is a pure function -- every run mints fresh pattern_ids for whatever it
    # currently detects, with no memory of prior runs. Re-identify each freshly-detected pattern
    # against last week's active patterns by its real identity (type + who it's about) so a
    # still-active pattern keeps its row (and its has_been_surfaced/surface_count/
    # user_acknowledged history) instead of duplicating as a new, unsurfaced row every week --
    # which would also silently defeat gate_3_recency's repeat-block.
    def _key(p):
        return (p.pattern_type, tuple(sorted(p.person_ids_involved)))

    prior_by_key = {_key(p): p for p in store.active_patterns(uid)}
    for pattern in patterns:
        prior = prior_by_key.pop(_key(pattern), None)
        if prior is not None:
            pattern.pattern_id = prior.pattern_id
            pattern.has_been_surfaced = prior.has_been_surfaced
            pattern.surface_count = prior.surface_count
            pattern.user_acknowledged = prior.user_acknowledged
            pattern.last_activation = prior.last_activation

    # Whatever's left in prior_by_key was active last run but isn't active this run (the
    # conflict resolved, the topic stopped recurring, etc.) -- deactivate rather than leave a
    # stale pattern permanently eligible for gate_1_availability.
    stale = list(prior_by_key.values())
    for p in stale:
        p.is_active = False
    store.save_patterns(uid, patterns + stale)
    logger.info("social pattern detection: nodes=%d events=%d patterns=%d stale=%d",
               len(graph.nodes), len(events), len(patterns), len(stale))
    return {"nodes": len(graph.nodes), "events": len(events), "patterns": len(patterns)}
