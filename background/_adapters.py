"""Map persisted Layer-2 state into the Layer-10 record shapes the longitudinal jobs consume.

Keeps the background jobs honest: they operate on what is actually persisted (episodes, sessions)
rather than synthetic inputs, translating each into the minimal Layer-10 record the engines expect.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import infra.db.models as m
from infra.db.engine import session_scope


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.now(timezone.utc).date()


def episodic_records(memory_store, user_id) -> list:
    """Active persisted episodes → Layer-10 EpisodicRecord list."""
    from backend.layer10_longitudinal.schemas import EpisodicRecord
    out = []
    for ep in memory_store.active_episodic(user_id):
        out.append(EpisodicRecord(
            episode_id=str(ep.memory_id), date=_as_date(getattr(ep, "created_at", None)),
            importance_score=float(getattr(ep, "importance_score", 0.0) or 0.0),
            emotional_intensity=abs(float(getattr(ep, "content_basis_valence", 0.0) or 0.0)),
            topics=list(getattr(ep, "topic_tags", []) or []),
            title=(getattr(ep, "summary", "") or "")[:80]))
    return out


def session_records(session_factory, user_id) -> list:
    """Persisted Session rows → Layer-10 SessionRecord list (turn_count as a duration proxy)."""
    from backend.layer10_longitudinal.schemas import SessionRecord
    with session_scope(session_factory) as s:
        rows = s.query(m.Session).filter_by(user_id=str(user_id)).all()
        return [SessionRecord(session_id=r.session_key, date=_as_date(r.created_at),
                              duration_mins=float(r.turn_count or 0)) for r in rows]
