"""Postgres-backed Layer-13 InitialState — the real SC-2 cold-start context record.

One row per user (a singleton, like RelationshipState/FormatProfile). Persists the same
InitialState dataclass ColdStartContextBuilder/GraduationEvaluator operate on, so passive
elicitation signals actually survive across turns and restarts instead of resetting every call.
"""
from __future__ import annotations

from typing import Optional

from backend.layer13_onboarding.context_constructor import make_initial_state
from backend.layer13_onboarding.schemas import InitialState
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresInitialStateStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def load(self) -> InitialState:
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            payload = dict(row.payload or {}) if row is not None else {}
            raw = payload.get("initial_state")
            if raw is None:
                return make_initial_state(self._user_id)
            return from_jsonable(InitialState, raw)

    def save(self, state: InitialState) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            if row is None:
                row = m.OnboardingState(user_id=self._user_id, cold_start_active=True, payload={})
                s.add(row)
            payload = dict(row.payload or {})
            payload["initial_state"] = to_jsonable(state)
            row.payload = payload
