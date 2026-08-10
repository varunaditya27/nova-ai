"""People route — read-only view of Layer 5's persisted social graph (single-user).

Reads directly from PostgresSocialStore, the real source of truth. UserWorldModel.relationship_graph
is a narrower derived projection of the same data (api/state.py::make_social_writer) and is not
read here — see docs/superpowers/specs/2026-08-10-social-graph-api-design.md §1.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import PersonDetailOut, PersonOut, SocialEventOut, SocialPatternOut
from infra.db.social_store import PostgresSocialStore

router = APIRouter(prefix="/people", tags=["people"])


def _iso(v):
    return v.isoformat() if v else None


def _person_out(node) -> PersonOut:
    return PersonOut(
        person_id=node.person_id, display_name=node.display_name,
        relationship_type=node.relationship_type,
        relationship_valence=node.relationship_valence, valence_trend=node.valence_trend,
        interaction_frequency=node.interaction_frequency,
        is_support_source=node.is_support_source, active_conflict=node.active_conflict,
        mention_count=node.mention_count, last_mentioned=_iso(node.last_mentioned))


def _event_out(event) -> SocialEventOut:
    return SocialEventOut(
        event_id=event.event_id, event_type=event.event_type, summary=event.summary,
        event_valence=event.event_valence, event_timestamp=_iso(event.event_timestamp),
        is_resolved=event.is_resolved)


def _pattern_out(pattern) -> SocialPatternOut:
    return SocialPatternOut(
        pattern_id=pattern.pattern_id, pattern_type=pattern.pattern_type,
        plain_language_description=pattern.plain_language_description,
        pattern_confidence=pattern.pattern_confidence, is_active=pattern.is_active)


@router.get("", response_model=list[PersonOut])
def list_people(state=Depends(get_state)):
    store = PostgresSocialStore(state.session_factory)
    graph = store.load_graph(state.default_user_id)
    nodes = list(graph.nodes.values()) if graph else []
    nodes.sort(key=lambda n: n.mention_count, reverse=True)
    return [_person_out(n) for n in nodes]


@router.get("/{person_id}", response_model=PersonDetailOut)
def get_person(person_id: str, state=Depends(get_state)):
    store = PostgresSocialStore(state.session_factory)
    graph = store.load_graph(state.default_user_id)
    node = graph.nodes.get(person_id) if graph else None
    if node is None:
        raise HTTPException(status_code=404, detail="person not found")

    events = [e for e in store.recent_events(state.default_user_id) if e.person_id == person_id]
    patterns = [p for p in store.active_patterns(state.default_user_id)
                if person_id in p.person_ids_involved]

    base = _person_out(node)
    return PersonDetailOut(
        **base.model_dump(),
        recent_events=[_event_out(e) for e in events],
        active_patterns=[_pattern_out(p) for p in patterns])
