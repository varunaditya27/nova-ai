"""Postgres-backed Layer-5 social intelligence store.

Three tables (`infra/db/models/social.py`): `social_graph` (one row per user, the whole
`SocialGraph`), `social_event` (one row per detected interpersonal event), `social_pattern`
(one row per detected social pattern, batch-computed by the background job). Same shape as
`PostgresMemoryStore`'s UWM/narrative-chain methods — short-lived `session_scope`s, callers
only ever see reconstructed dataclasses.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.layer5_relationship.schemas import SocialEvent, SocialGraph, SocialPattern
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable
from infra.db.social_serde import graph_from_jsonable, graph_to_jsonable


class PostgresSocialStore:
    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    # ── SC-1 Social Graph ────────────────────────────────────────────────
    def load_graph(self, user_id) -> Optional[SocialGraph]:
        with session_scope(self._sf) as s:
            row = s.query(m.SocialGraph).filter_by(user_id=str(user_id)).one_or_none()
            return graph_from_jsonable(row.payload) if row else None

    def save_graph(self, graph: SocialGraph) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.SocialGraph).filter_by(user_id=str(graph.user_id)).one_or_none()
            payload = graph_to_jsonable(graph)
            if row is None:
                s.add(m.SocialGraph(user_id=str(graph.user_id), payload=payload))
            else:
                row.payload = payload

    # ── SC-2 Social Events ───────────────────────────────────────────────
    def save_event(self, user_id, event: SocialEvent) -> str:
        with session_scope(self._sf) as s:
            row = s.query(m.SocialEvent).filter_by(event_id=str(event.event_id)).one_or_none()
            if row is None:
                s.add(m.SocialEvent(
                    user_id=str(user_id), event_id=str(event.event_id),
                    person_id=str(event.person_id), payload=to_jsonable(event)))
            else:
                row.payload = to_jsonable(event)
        return event.event_id

    def recent_events(self, user_id, limit: int = 200) -> list[SocialEvent]:
        """Most recently reported events first, capped -- pattern_recognizer.detect_patterns
        wants the event history, not a windowed query; capped so a years-old account doesn't
        load an unbounded list into the batch job."""
        with session_scope(self._sf) as s:
            rows = (s.query(m.SocialEvent).filter_by(user_id=str(user_id))
                    .order_by(m.SocialEvent.id.desc()).limit(limit).all())
            return [from_jsonable(SocialEvent, r.payload) for r in rows]

    # ── SC-3 Social Patterns ─────────────────────────────────────────────
    def save_patterns(self, user_id, patterns: list[SocialPattern]) -> None:
        with session_scope(self._sf) as s:
            for pattern in patterns:
                row = (s.query(m.SocialPattern)
                       .filter_by(pattern_id=str(pattern.pattern_id)).one_or_none())
                payload = to_jsonable(pattern)
                if row is None:
                    s.add(m.SocialPattern(
                        user_id=str(user_id), pattern_id=str(pattern.pattern_id),
                        is_active=pattern.is_active, payload=payload))
                else:
                    row.is_active = pattern.is_active
                    row.payload = payload

    def active_patterns(self, user_id) -> list[SocialPattern]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.SocialPattern)
                    .filter_by(user_id=str(user_id), is_active=True).all())
            return [from_jsonable(SocialPattern, r.payload) for r in rows]

    def mark_pattern_surfaced(self, pattern_id, now: Optional[datetime] = None) -> None:
        """gate_3_recency (§6.4) needs has_been_surfaced/surface_count/last_activation to ever
        actually block a repeat -- without this write path, the same coaching observation would
        re-qualify on every gate-1-passing turn forever."""
        now = now or datetime.now(timezone.utc)
        with session_scope(self._sf) as s:
            row = s.query(m.SocialPattern).filter_by(pattern_id=str(pattern_id)).one_or_none()
            if row is None:
                return
            pattern = from_jsonable(SocialPattern, row.payload)
            pattern.has_been_surfaced = True
            pattern.surface_count += 1
            pattern.last_activation = now
            pattern.last_observed = now   # gate_3_recency's own recency check reads this field
            row.payload = to_jsonable(pattern)
