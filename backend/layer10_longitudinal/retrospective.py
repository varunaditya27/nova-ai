"""SC-4 — Retrospective Engine (architecture doc §6).

Generates time-anchored "look back" reflections (one week / month / year ago, milestones,
Year in Review). Reflections are grounded in specific episodic memories (`backing_episode_ids`)
and never fabricate (§13.3). Interpretive prose comes from an injected ``llm_fn`` with a grounded
factual fallback; surfacing windows and priorities are deterministic.

Static tables live in ``retrospective_tables.py``; then/now comparison and parsing helpers live
in ``retrospective_helpers.py``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

from backend.layer10_longitudinal.retrospective_helpers import (
    as_date,
    build_then_vs_now,
    coerce_llm_json,
    nearest_weekly_summary,
)
from backend.layer10_longitudinal.retrospective_tables import (
    LABELS,
    SURFACING_WINDOWS,
    compute_surfacing_priority,
)
from backend.layer10_longitudinal.schemas import RetrospectivePacket, YearInReview

__all__ = [
    "SURFACING_WINDOWS", "compute_surfacing_priority", "build_then_vs_now",
    "generate_retrospective", "generate_year_in_review",
]


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
    then_goals = [g for g in goals if (as_date(getattr(g, "created_at", None)) or current_date)
                  <= reference_date]
    current_goals = [g for g in goals if getattr(g, "status", "") == "active"]
    then_summary = nearest_weekly_summary(weekly_summaries, reference_date)
    then_vs_now = build_then_vs_now(then_episodes, then_summary, then_goals, progress_record, current_goals)

    growth_highlights = []
    if getattr(progress_record, "avg_valence_4w", 0.0) > 0.1:
        growth_highlights.append("Emotional wellbeing has trended positive recently.")

    label = LABELS.get(retrospective_type, "Looking back")
    headline, narrative, questions = "", "", []
    if llm_fn is not None:
        try:
            data = coerce_llm_json(llm_fn(f"Write a {retrospective_type} retrospective for "
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
    started = [g for g in goals if _in_year(as_date(getattr(g, "created_at", None)))]
    achieved = [g for g in goals if getattr(g, "status", "") == "completed"
                and _in_year(as_date(getattr(g, "status_changed_at", None)))]
    abandoned = [g for g in goals if getattr(g, "status", "") == "abandoned"
                 and _in_year(as_date(getattr(g, "status_changed_at", None)))]
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
