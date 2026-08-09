"""Postgres-backed per-user Layer-4/5 relationship state.

Persists the Layer-4 ``RelationshipState`` domain object (JSONB) and advances it each turn: message
and session counters climb, and the qualitative ``stage`` follows the architecture's session
thresholds (new → acquaintance → developing → established → close). This is the durable substrate
for relationship deepening — the headline long-term-companionship behaviour. Bound to one user.
"""
from __future__ import annotations

from backend.layer4_persona.relationship_manager import (
    compute_session_delta, stage_for_sessions, update_tie_strength,
)
from backend.layer4_persona.schemas import RelationshipState, SessionSummary
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


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

    def first_session_date(self):
        """The row's own creation timestamp -- the real 'day 1 with Nova' signal, set the moment
        record_turn first ran for this user. Returns None if the relationship hasn't started yet."""
        with session_scope(self._sf) as s:
            row = s.query(m.RelationshipState).filter_by(user_id=self._user_id).one_or_none()
            return row.created_at.date() if row is not None else None

    def save(self, state: RelationshipState) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.RelationshipState).filter_by(user_id=self._user_id).one_or_none()
            payload = to_jsonable(state)
            if row is None:
                s.add(m.RelationshipState(user_id=self._user_id, stage=state.stage, payload=payload))
            else:
                row.stage = state.stage
                row.payload = payload

    def record_turn(self, session_key: str, user_message: str = "",
                     emotional_intensity: float = 0.0,
                     had_vulnerability_moment: bool = False) -> RelationshipState:
        """Advance the relationship for one turn: bump message count, count a distinct session,
        recompute the qualitative stage, and — when a message is supplied — learn the user's
        communication style (verbosity/formality/question & advice tolerance). Returns the state.

        Tie strength (architecture doc §4.3) is meant to update once per session, but this
        continuous-chat system has no explicit "session end" event. So per-turn signals
        (`emotional_intensity`, `had_vulnerability_moment`) accumulate into the payload — outside
        the dataclass, same convention as `_counted_session_keys` — and the accumulated
        `SessionSummary` is applied via `compute_session_delta`/`update_tie_strength` the moment a
        new `session_key` is observed, i.e. retroactively for the session that just ended.
        `explicit_trust_signals_count`/`repair_occurred` have no real detector anywhere yet, so
        they stay at their falsy defaults — an honest degradation, not a fabricated signal."""
        with session_scope(self._sf) as s:
            row = s.query(m.RelationshipState).filter_by(user_id=self._user_id).one_or_none()
            prior = dict(row.payload) if row else {}
            state = from_jsonable(RelationshipState, prior) if row else RelationshipState()
            keys = set(prior.get("_counted_session_keys", []) or [])
            key = str(session_key or "default")

            prev_key = prior.get("_current_session_key")
            session_messages = int(prior.get("_current_session_message_count", 0))
            session_max_intensity = float(prior.get("_current_session_max_intensity", 0.0))
            session_had_vulnerability = bool(prior.get("_current_session_had_vulnerability", False))
            if prev_key and prev_key != key:
                summary = SessionSummary(
                    had_vulnerability_moment=session_had_vulnerability,
                    total_messages=session_messages,
                    max_emotional_intensity=session_max_intensity)
                delta = compute_session_delta(summary)
                state.tie_strength = update_tie_strength(state.tie_strength, delta)
                state.vulnerability_moments += int(summary.had_vulnerability_moment)
                session_messages, session_max_intensity, session_had_vulnerability = 0, 0.0, False

            session_messages += 1
            session_max_intensity = max(session_max_intensity, emotional_intensity)
            session_had_vulnerability = session_had_vulnerability or had_vulnerability_moment

            state.total_messages_exchanged += 1
            if key not in keys:
                keys.add(key)
                state.total_sessions += 1
            state.stage = stage_for_sessions(state.total_sessions)
            if user_message:
                from backend.layer4_persona.style_learning import learn_communication_style
                learn_communication_style(state, user_message)
            payload = to_jsonable(state)
            payload["_counted_session_keys"] = sorted(keys)   # tracked outside the dataclass
            payload["_current_session_key"] = key
            payload["_current_session_message_count"] = session_messages
            payload["_current_session_max_intensity"] = session_max_intensity
            payload["_current_session_had_vulnerability"] = session_had_vulnerability
            if row is None:
                s.add(m.RelationshipState(user_id=self._user_id, stage=state.stage, payload=payload))
            else:
                row.stage = state.stage
                row.payload = payload
            return state
