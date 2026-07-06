"""Postgres-backed per-user Layer-4/5 relationship state.

Persists the Layer-4 ``RelationshipState`` domain object (JSONB) and advances it each turn: message
and session counters climb, and the qualitative ``stage`` follows the architecture's session
thresholds (new → acquaintance → developing → established → close). This is the durable substrate
for relationship deepening — the headline long-term-companionship behaviour. Bound to one user.
"""
from __future__ import annotations

from backend.layer4_persona.schemas import RelationshipState
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable

# Architecture doc §4.2 session thresholds.
_STAGE_THRESHOLDS = [(100, "close"), (41, "established"), (16, "developing"), (4, "acquaintance")]


def stage_for_sessions(total_sessions: int) -> str:
    for floor, stage in _STAGE_THRESHOLDS:
        if total_sessions >= floor:
            return stage
    return "new"


class PostgresRelationshipStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def load(self) -> RelationshipState:
        with session_scope(self._sf) as s:
            row = s.query(m.RelationshipState).filter_by(user_id=self._user_id).one_or_none()
            if row is None:
                return RelationshipState()
            return from_jsonable(RelationshipState, dict(row.payload))

    def save(self, state: RelationshipState) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.RelationshipState).filter_by(user_id=self._user_id).one_or_none()
            payload = to_jsonable(state)
            if row is None:
                s.add(m.RelationshipState(user_id=self._user_id, stage=state.stage, payload=payload))
            else:
                row.stage = state.stage
                row.payload = payload

    def record_turn(self, session_key: str) -> RelationshipState:
        """Advance the relationship for one turn: bump message count, count a distinct session, and
        recompute the qualitative stage. Returns the updated state."""
        with session_scope(self._sf) as s:
            row = s.query(m.RelationshipState).filter_by(user_id=self._user_id).one_or_none()
            prior = dict(row.payload) if row else {}
            state = from_jsonable(RelationshipState, prior) if row else RelationshipState()
            keys = set(prior.get("_counted_session_keys", []) or [])
            key = str(session_key or "default")
            state.total_messages_exchanged += 1
            if key not in keys:
                keys.add(key)
                state.total_sessions += 1
            state.stage = stage_for_sessions(state.total_sessions)
            payload = to_jsonable(state)
            payload["_counted_session_keys"] = sorted(keys)   # tracked outside the dataclass
            if row is None:
                s.add(m.RelationshipState(user_id=self._user_id, stage=state.stage, payload=payload))
            else:
                row.stage = state.stage
                row.payload = payload
            return state
