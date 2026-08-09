"""Continuity routes — the Digital Desk, calendar heatmap, and museum of firsts (single-user).

These are lenses derived over data other layers already produce (longitudinal narratives, goals,
proactive queue, relationship state, the message log) — the chat is never touched.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import CalendarOut, HomeOut, MuseumEntryOut, MuseumOut
from infra.db.goal_store import PostgresGoalStore
from infra.db.longitudinal_store import PostgresLongitudinalStore
from infra.db.message_store import PostgresMessageStore
from infra.db.onboarding_store import PostgresOnboardingStore
from infra.db.proactive_store import PostgresProactiveQueue
from infra.db.relationship_store import PostgresRelationshipStore
from backend.layer7_goals.schemas import GoalStatus

router = APIRouter(tags=["continuity"])
_ACTIVE = [GoalStatus.ACTIVE.value, GoalStatus.ON_TRACK.value, GoalStatus.AT_RISK.value]


def _greeting(now: datetime, timezone_offset_hours: float = 0.0) -> str:
    h = (now + timedelta(hours=timezone_offset_hours)).hour
    if h < 5:
        return "Good evening"
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


def _weather(last: Optional[datetime], now: datetime) -> str:
    if last is None:
        return "clear"
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    days = (now - last).total_seconds() / 86400.0
    if days < 1:
        return "sunny"
    if days < 4:
        return "clear"
    if days < 10:
        return "cloudy"
    return "distant"


def _iso(v):
    return v.isoformat() if v is not None and hasattr(v, "isoformat") else None


@router.get("/home", response_model=HomeOut)
def home(state=Depends(get_state)):
    sf, uid = state.session_factory, state.default_user_id
    now = datetime.now(timezone.utc)
    grad = state.config.get("onboarding", {}).get("graduation_sessions", 5)
    tz_offset = state.config.get("system", {}).get("timezone_offset_hours", 0.0)
    try:
        arc = PostgresLongitudinalStore(sf, uid).load_narrative_arc()
        chapter = None
        if arc is not None and arc.current_chapter is not None:
            # The real Layer-10 SC-1 chapter object (narrative_arc_job.py, weekly synthesis) --
            # title first, falling back to its narrative summary, not an unrelated weekly
            # summary's dominant_theme (which was never actually "the current chapter").
            chapter = arc.current_chapter.title or arc.current_chapter.narrative_summary or None
        rel = PostgresRelationshipStore(sf, uid).load()
        msgs = PostgresMessageStore(sf, uid)
        last_at = msgs.last_interaction_at()
        goals = PostgresGoalStore(sf, uid).load_by_status(_ACTIVE)
        proactive = PostgresProactiveQueue(sf, uid).load(statuses=["pending", "deferred"])
        proactive.sort(key=lambda i: getattr(i, "current_priority", 0.0), reverse=True)
        top = getattr(proactive[0], "content_basis", None) if proactive else None
        cold = PostgresOnboardingStore(sf, uid, grad).state().get("cold_start_active", False)
    except Exception:
        raise HTTPException(status_code=503, detail="home temporarily unavailable")
    return HomeOut(
        greeting=_greeting(now, tz_offset), current_chapter=(chapter[:280] if chapter else None),
        relationship_stage=rel.stage, last_interaction_at=_iso(last_at),
        weather=_weather(last_at, now), active_goals=len(goals),
        top_proactive=(top[:200] if top else None), cold_start_active=bool(cold),
        message_count=msgs.count())


@router.get("/calendar", response_model=CalendarOut)
def calendar(start: Optional[str] = None, end: Optional[str] = None, state=Depends(get_state)):
    now = datetime.now(timezone.utc)
    try:
        s = datetime.fromisoformat(start) if start else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        e = datetime.fromisoformat(end) if end else now
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid start/end datetime")
    tz_offset = state.config.get("system", {}).get("timezone_offset_hours", 0.0)
    try:
        days = PostgresMessageStore(state.session_factory, state.default_user_id).day_activity(
            s, e, tz_offset)
    except Exception:
        raise HTTPException(status_code=503, detail="calendar temporarily unavailable")
    return CalendarOut(start=_iso(s), end=_iso(e), days=days)


@router.get("/museum", response_model=MuseumOut)
def museum(state=Depends(get_state)):
    sf, uid = state.session_factory, state.default_user_id
    entries: list[MuseumEntryOut] = []
    try:
        msgs = PostgresMessageStore(sf, uid)
        first = msgs.first()
        if first is not None:
            entries.append(MuseumEntryOut(label="First conversation",
                                          content=(first.get("content") or "")[:200],
                                          when=_iso(first.get("created_at"))))
        milestones = msgs.list_milestones()
        if milestones:
            m0 = milestones[0]
            entries.append(MuseumEntryOut(label="First milestone",
                                          content=(m0.get("milestone_label") or m0.get("content") or "")[:200],
                                          when=_iso(m0.get("created_at"))))
        goals = PostgresGoalStore(sf, uid).load_by_status(
            _ACTIVE + [GoalStatus.ACHIEVED.value] if hasattr(GoalStatus, "ACHIEVED") else _ACTIVE)
        dated = sorted((g for g in goals if getattr(g, "created_at", None)),
                       key=lambda g: g.created_at)
        if dated:
            entries.append(MuseumEntryOut(label="First goal", content=(dated[0].title or "")[:200],
                                          when=_iso(dated[0].created_at)))
    except Exception:
        raise HTTPException(status_code=503, detail="museum temporarily unavailable")
    return MuseumOut(entries=entries)
