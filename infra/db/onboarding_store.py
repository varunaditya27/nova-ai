"""Postgres-backed Layer-13 onboarding state — self-graduating session counter.

Persists a per-user cold-start record: an active flag plus a count of distinct sessions (tracked by
key so a session is counted once). Graduates (clears the flag) at ``graduation_sessions``. Bound to
one user; all queries are user-scoped.
"""
from __future__ import annotations

import infra.db.models as m
from infra.db.engine import session_scope

_DEFAULTS = {"session_index": 0, "counted_session_keys": []}


class PostgresOnboardingStore:
    def __init__(self, session_factory, user_id, graduation_sessions: int = 5) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)
        self._grad = graduation_sessions

    def state(self) -> dict:
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            if row is None:
                return {"cold_start_active": True, **{k: (list(v) if isinstance(v, list) else v)
                                                      for k, v in _DEFAULTS.items()}}
            payload = dict(row.payload or {})
            return {"cold_start_active": row.cold_start_active,
                    "session_index": payload.get("session_index", 0),
                    "counted_session_keys": list(payload.get("counted_session_keys", []))}

    def record_turn(self, session_key) -> None:
        key = str(session_key or "default")
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            if row is None:
                row = m.OnboardingState(user_id=self._user_id, cold_start_active=True,
                                        payload=dict(_DEFAULTS))
                s.add(row)
            payload = dict(row.payload or _DEFAULTS)
            counted = list(payload.get("counted_session_keys", []))
            if key not in counted:
                counted.append(key)
                payload["counted_session_keys"] = counted
                payload["session_index"] = payload.get("session_index", 0) + 1
                if payload["session_index"] >= self._grad:
                    row.cold_start_active = False
                row.payload = payload
