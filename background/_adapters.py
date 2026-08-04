"""Map persisted Layer-2 state into the Layer-10 record shapes the longitudinal jobs consume.

Keeps the background jobs honest: they operate on what is actually persisted (episodes, sessions)
rather than synthetic inputs, translating each into the minimal Layer-10 record the engines expect.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import infra.db.models as m
from infra.db.engine import session_scope


def _as_date(value, timezone_offset_hours: float = 0.0) -> date:
    """Local calendar date for a stored (UTC) timestamp.

    Must use the same offset as Layer 1's live circadian band (docs/layer-1-architecture.md
    §16) — otherwise late-night-local activity that crosses the UTC day boundary gets
    attributed to the wrong day, silently skewing Layer 10's day-of-week pattern detector.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (value + timedelta(hours=timezone_offset_hours)).date()
    if isinstance(value, date):
        return value
    return (datetime.now(timezone.utc) + timedelta(hours=timezone_offset_hours)).date()


def _episode_valence(ep) -> float:
    """EpisodicMemory's emotion field is ``emotion_vector.valence`` -- there is no
    ``content_basis_valence`` on the schema (that name belongs to Layer 6's ProactiveItem)."""
    return float(getattr(getattr(ep, "emotion_vector", None), "valence", 0.0) or 0.0)


def episodic_records(memory_store, user_id, timezone_offset_hours: float = 0.0) -> list:
    """Active persisted episodes → Layer-10 EpisodicRecord list."""
    from backend.layer10_longitudinal.schemas import EpisodicRecord
    out = []
    for ep in memory_store.active_episodic(user_id):
        out.append(EpisodicRecord(
            episode_id=str(ep.memory_id),
            date=_as_date(getattr(ep, "created_at", None), timezone_offset_hours),
            importance_score=float(getattr(ep, "importance_score", 0.0) or 0.0),
            emotional_intensity=abs(_episode_valence(ep)),
            topics=list(getattr(ep, "topic_tags", []) or []),
            title=(getattr(ep, "summary", "") or "")[:80]))
    return out


def emotional_records(memory_store, user_id, timezone_offset_hours: float = 0.0) -> list:
    """Active persisted episodes → Layer-10 EmotionalRecord list (per-episode emotion snapshot).

    Layer 10 has no dedicated per-message emotional history log yet (see POLISH_BACKLOG.md); each
    episode's ``emotion_vector`` is the nearest real signal available today, so it doubles as the
    emotional record source until a real per-turn log exists.
    """
    from backend.layer10_longitudinal.schemas import EmotionalRecord
    out = []
    for ep in memory_store.active_episodic(user_id):
        vec = getattr(ep, "emotion_vector", None)
        valence = float(getattr(vec, "valence", 0.0) or 0.0)
        arousal = float(getattr(vec, "arousal", 0.0) or 0.0)
        out.append(EmotionalRecord(
            date=_as_date(getattr(ep, "created_at", None), timezone_offset_hours),
            valence=valence, arousal=arousal,
            emotional_intensity=min(1.0, (valence ** 2 + arousal ** 2) ** 0.5 / (2 ** 0.5))))
    return out


def session_records(session_factory, user_id, timezone_offset_hours: float = 0.0) -> list:
    """Persisted Session rows → Layer-10 SessionRecord list (turn_count as a duration proxy)."""
    from backend.layer10_longitudinal.schemas import SessionRecord
    with session_scope(session_factory) as s:
        rows = s.query(m.Session).filter_by(user_id=str(user_id)).all()
        return [SessionRecord(session_id=r.session_key,
                              date=_as_date(r.created_at, timezone_offset_hours),
                              duration_mins=float(r.turn_count or 0)) for r in rows]
