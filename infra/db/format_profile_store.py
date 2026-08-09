"""Postgres-backed per-user Layer-9 UserFormatProfile.

Persists the learned format-preference record (§6.5-§6.6): preferred length, explicit
format-feedback overrides, and the bookkeeping fields the cross-turn skim-detection signal
needs (last_response_length/last_response_at). Bound to one user.
"""
from __future__ import annotations

from backend.layer9_output.schemas import UserFormatProfile
from backend.layer9_output.user_format_profile import initialize_defaults
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresFormatProfileStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def load(self) -> UserFormatProfile:
        with session_scope(self._sf) as s:
            row = s.query(m.FormatProfile).filter_by(user_id=self._user_id).one_or_none()
            if row is None:
                return initialize_defaults(self._user_id)
            return from_jsonable(UserFormatProfile, dict(row.payload))

    def save(self, profile: UserFormatProfile) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.FormatProfile).filter_by(user_id=self._user_id).one_or_none()
            payload = to_jsonable(profile)
            if row is None:
                s.add(m.FormatProfile(user_id=self._user_id, payload=payload))
            else:
                row.payload = payload
