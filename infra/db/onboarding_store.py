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

    def elicitation_state(self, session_key=None) -> dict:
        """The persisted active-elicitation memory: which inference targets have already been
        surfaced, and whether one was already surfaced in this session (early-period rate limit)."""
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            payload = dict(row.payload or {}) if row is not None else {}
            surfaced = list(payload.get("surfaced_elicitation_targets", []))
            sessions = list(payload.get("elicitation_session_keys", []))
            return {"surfaced_targets": surfaced,
                    "asked_this_session": str(session_key or "default") in sessions}

    def record_elicitation(self, session_key, inference_target: str, asked_message: str = "") -> None:
        """Mark an inference target as surfaced (never re-ask it) and this session as having asked.
        The *next* user message is its answer: ``pending_answer`` remembers what was asked and the
        message that prompted it, so the asking turn itself is never mistaken for the reply."""
        key = str(session_key or "default")
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            if row is None:
                row = m.OnboardingState(user_id=self._user_id, cold_start_active=True,
                                        payload=dict(_DEFAULTS))
                s.add(row)
            payload = dict(row.payload or _DEFAULTS)
            targets = list(payload.get("surfaced_elicitation_targets", []))
            if inference_target and inference_target not in targets:
                targets.append(inference_target)
            payload["surfaced_elicitation_targets"] = targets
            payload["pending_answer"] = {"target": inference_target, "asked_message": asked_message}
            sessions = list(payload.get("elicitation_session_keys", []))
            if key not in sessions:
                sessions.append(key)
            payload["elicitation_session_keys"] = sessions
            row.payload = payload

    def take_pending_answer(self, current_message: str) -> str | None:
        """The inference target awaiting an answer, if ``current_message`` is a later message than
        the one that asked it; clears it. None when nothing is pending or this is the asking turn."""
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            payload = dict(row.payload or {}) if row is not None else {}
            pending = payload.get("pending_answer")
            if not pending or pending.get("asked_message") == current_message:
                return None
            payload.pop("pending_answer")
            row.payload = payload
            return pending["target"]

    def graduate_now(self) -> None:
        """Explicitly end cold start ahead of the session-counter fallback -- called when the
        real GraduationEvaluator's criteria are satisfied before the bare session count reaches
        graduation_sessions (docs/layer-13-architecture.md)."""
        with session_scope(self._sf) as s:
            row = s.query(m.OnboardingState).filter_by(user_id=self._user_id).one_or_none()
            if row is None:
                row = m.OnboardingState(user_id=self._user_id, cold_start_active=False,
                                        payload=dict(_DEFAULTS))
                s.add(row)
            else:
                row.cold_start_active = False

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
