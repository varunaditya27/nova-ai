"""SC-4 — Retrospective Engine (architecture doc §6).

Generates time-anchored "look back" reflections (one week / month / year ago, milestones,
Year in Review). Reflections are grounded in specific episodic memories (`backing_episode_ids`)
and never fabricate (§13.3). Interpretive prose comes from an injected ``llm_fn`` with a grounded
factual fallback; surfacing windows and priorities are deterministic.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Callable, Optional

from backend.layer10_longitudinal.schemas import (
    RetrospectivePacket,
    RetrospectiveType,
    ThenVsNow,
    YearInReview,
)

# Surfacing windows in days (architecture doc §6.3).
SURFACING_WINDOWS = {
    RetrospectiveType.ONE_WEEK_AGO.value: 3,
    RetrospectiveType.ONE_MONTH_AGO.value: 7,
    RetrospectiveType.THREE_MONTHS_AGO.value: 14,
    RetrospectiveType.SIX_MONTHS_AGO.value: 21,
    RetrospectiveType.ONE_YEAR_AGO.value: 30,
    RetrospectiveType.GOAL_ANNIVERSARY.value: 14,
    RetrospectiveType.CHAPTER_CLOSE.value: 7,
    RetrospectiveType.RELATIONSHIP_MILESTONE.value: 3,
    RetrospectiveType.FIRST_YEAR_IN_REVIEW.value: 60,
    RetrospectiveType.QUARTERLY_GROWTH.value: 14,
    RetrospectiveType.PATTERN_SURFACING.value: 21,
}

# Base surfacing priority by type — depth of output matches depth of moment (§13.5).
_BASE_PRIORITY = {
    RetrospectiveType.ONE_WEEK_AGO.value: 0.30,
    RetrospectiveType.ONE_MONTH_AGO.value: 0.45,
    RetrospectiveType.THREE_MONTHS_AGO.value: 0.55,
    RetrospectiveType.SIX_MONTHS_AGO.value: 0.70,
    RetrospectiveType.ONE_YEAR_AGO.value: 0.85,
    RetrospectiveType.GOAL_ANNIVERSARY.value: 0.60,
    RetrospectiveType.CHAPTER_CLOSE.value: 0.60,
    RetrospectiveType.RELATIONSHIP_MILESTONE.value: 0.70,
    RetrospectiveType.FIRST_YEAR_IN_REVIEW.value: 0.95,
    RetrospectiveType.QUARTERLY_GROWTH.value: 0.55,
    RetrospectiveType.PATTERN_SURFACING.value: 0.60,
}

_LABELS = {
    RetrospectiveType.ONE_WEEK_AGO.value: "A week ago",
    RetrospectiveType.ONE_MONTH_AGO.value: "A month ago",
    RetrospectiveType.THREE_MONTHS_AGO.value: "Three months ago",
    RetrospectiveType.SIX_MONTHS_AGO.value: "Six months ago",
    RetrospectiveType.ONE_YEAR_AGO.value: "A year ago",
}


def _as_date(value) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def compute_surfacing_priority(
    retrospective_type: str, significance_of_reference_date: float, growth_magnitude: int,
) -> float:
    """Blend type base, reference-date significance, and growth into a [0,1] priority (§6.3)."""
    base = _BASE_PRIORITY.get(retrospective_type, 0.5)
    growth = min(growth_magnitude, 5) / 5
    priority = base * 0.6 + significance_of_reference_date * 0.25 + growth * 0.15
    return round(max(0.0, min(1.0, priority)), 4)


def build_then_vs_now(then_episodes, then_summary, then_goals, current_progress, current_goals) -> ThenVsNow:
    """A structured then/now comparison (architecture doc §6.3 step 2)."""
    then_concern = then_episodes[0].title if then_episodes else "—"
    now_concern = current_goals[0].title if current_goals else "—"

    then_emotion = "unknown"
    if then_summary is not None and getattr(then_summary, "emotional_summary", None) is not None:
        then_emotion = then_summary.emotional_summary.dominant_emotion

    now_valence = getattr(current_progress, "avg_valence_4w", 0.0)
    if now_valence > 0.15:
        now_emotion = "positive"
    elif now_valence < -0.15:
        now_emotion = "negative"
    else:
        now_emotion = "neutral"

    then_count, now_count = len(then_goals), len(current_goals)
    if now_count > then_count:
        key_change = f"{now_count - then_count} new active goal(s) since then."
    elif now_count < then_count:
        key_change = f"{then_count - now_count} fewer active goal(s) than then."
    else:
        key_change = "Similar goal load to then."

    return ThenVsNow(
        then_primary_concern=then_concern, now_primary_concern=now_concern,
        then_emotional_state=then_emotion, now_emotional_state=now_emotion,
        then_active_goals=[getattr(g, "title", str(g)) for g in then_goals],
        now_active_goals=[getattr(g, "title", str(g)) for g in current_goals],
        key_change=key_change)


def _nearest_weekly_summary(weekly_summaries: list, reference_date: date):
    """The weekly summary whose week is nearest to reference_date, or None (§6.3)."""
    if not weekly_summaries:
        return None
    return min(weekly_summaries, key=lambda w: abs((w.week_start_date - reference_date).days))


def _coerce(raw) -> Optional[dict]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None
    return None


def generate_retrospective(
    retrospective_type: str,
    reference_date: date,
    current_date: date,
    narrative_arc,
    weekly_summaries: list,
    progress_record,
    goals: list,
    episodic_memories: list,
    llm_fn: Optional[Callable[[str], object]] = None,
) -> RetrospectivePacket:
    """Generate a time-anchored retrospective packet (architecture doc §6.3)."""
    then_episodes = [e for e in episodic_memories
                     if abs((e.date - reference_date).days) <= 14]
    then_goals = [g for g in goals if (_as_date(getattr(g, "created_at", None)) or current_date)
                  <= reference_date]
    current_goals = [g for g in goals if getattr(g, "status", "") == "active"]
    then_summary = _nearest_weekly_summary(weekly_summaries, reference_date)
    then_vs_now = build_then_vs_now(then_episodes, then_summary, then_goals, progress_record, current_goals)

    growth_highlights = []
    if getattr(progress_record, "avg_valence_4w", 0.0) > 0.1:
        growth_highlights.append("Emotional wellbeing has trended positive recently.")

    label = _LABELS.get(retrospective_type, "Looking back")
    headline, narrative, questions = "", "", []
    if llm_fn is not None:
        try:
            data = _coerce(llm_fn(f"Write a {retrospective_type} retrospective for "
                                  f"reference date {reference_date}."))
        except Exception:
            data = None
        if data is not None:
            headline = data.get("headline", "")
            narrative = data.get("narrative", "")
            questions = data.get("questions", []) or []
    if not headline:
        headline = f"{label}, around {reference_date.isoformat()}."
    if not narrative:
        n = len(then_episodes)
        narrative = (f"{label}, there {'were' if n != 1 else 'was'} {n} "
                     f"notable moment(s) on record around that time.")

    significance = max((getattr(e, "importance_score", 0.0) for e in then_episodes), default=0.5)
    priority = compute_surfacing_priority(retrospective_type, significance, len(growth_highlights))

    return RetrospectivePacket(
        user_id=getattr(narrative_arc, "user_id", ""), retrospective_type=retrospective_type,
        reference_date=reference_date, generated_at=datetime.utcnow(), headline=headline,
        narrative_reflection=narrative, then_vs_now=then_vs_now,
        growth_highlights=growth_highlights, reflection_questions=questions,
        backing_episode_ids=[e.episode_id for e in then_episodes],
        surfacing_priority=priority,
        surfacing_window_days=SURFACING_WINDOWS.get(retrospective_type, 7))


def generate_year_in_review(
    user_id: str,
    year_start: date,
    year_end: date,
    narrative_arc,
    all_weekly_summaries: list,
    progress_record,
    goals: list,
    llm_fn: Optional[Callable[[str], object]] = None,
) -> YearInReview:
    """Annual synthesis — the highest-stakes Layer 10 output (architecture doc §6.4)."""
    def _in_year(d):
        return d is not None and year_start <= d <= year_end

    # Layer 7's real GoalStatus terminal value is "completed", not "achieved" -- see
    # progress_tracker.py's compute_progress_snapshot for the same fix and why it matters.
    started = [g for g in goals if _in_year(_as_date(getattr(g, "created_at", None)))]
    achieved = [g for g in goals if getattr(g, "status", "") == "completed"
                and _in_year(_as_date(getattr(g, "status_changed_at", None)))]
    abandoned = [g for g in goals if getattr(g, "status", "") == "abandoned"
                 and _in_year(_as_date(getattr(g, "status_changed_at", None)))]
    ongoing = [g for g in goals if getattr(g, "status", "") == "active"]

    year_weeklies = [w for w in all_weekly_summaries
                     if year_start <= w.week_start_date <= year_end and w.emotional_summary]
    hardest = min(year_weeklies, key=lambda w: w.emotional_summary.avg_valence, default=None)
    best = max(year_weeklies, key=lambda w: w.emotional_summary.avg_valence, default=None)

    return YearInReview(
        user_id=user_id, year=year_start.year,
        chapter_count=len(getattr(narrative_arc, "chapters", []) or []),
        total_sessions=sum(w.session_count for w in year_weeklies),
        goals_set=len(started), goals_achieved=len(achieved), goals_abandoned=len(abandoned),
        goals_carrying_forward=len(ongoing),
        hardest_period_summary=hardest.week_narrative if hardest else None,
        best_period_summary=best.week_narrative if best else None,
        year_narrative=f"A year with {len(started)} goals set and {len(achieved)} achieved.")
