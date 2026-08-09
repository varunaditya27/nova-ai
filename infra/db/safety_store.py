"""Postgres-backed append-only safety log for Layer-11 crisis assessments.

Records each meaningful ``CrisisSignal`` as a ``safety_event`` row (JSONB payload); never mutates
existing rows. ``recent`` feeds the (deferred) SC-4 dependency monitor.
"""
from __future__ import annotations

from backend.layer11_safety.schemas import CrisisSignal
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresSafetyLog:
    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    def record(self, signal: CrisisSignal) -> None:
        with session_scope(self._sf) as s:
            s.add(m.SafetyEvent(user_id=str(signal.user_id or ""), tier=signal.tier,
                                payload=to_jsonable(signal)))

    def recent(self, user_id, limit: int = 20) -> list[CrisisSignal]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.SafetyEvent).filter_by(user_id=str(user_id))
                    .order_by(m.SafetyEvent.id.desc()).limit(limit).all())
            return [from_jsonable(CrisisSignal, r.payload) for r in rows]

    def crisis_count(self, user_id) -> int:
        """Count of real crisis-tier events (excludes CrisisTier.NONE) -- feeds Layer-12's
        transparency audit view (§5.2)."""
        with session_scope(self._sf) as s:
            return (s.query(m.SafetyEvent)
                    .filter(m.SafetyEvent.user_id == str(user_id), m.SafetyEvent.tier != "none")
                    .count())
