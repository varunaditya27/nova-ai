"""SC-2 — Weekly Summary Engine (architecture doc §4).

Generates a synthesized digest of the past seven days: session aggregation, emotional texture
(vs. previous week and vs. an 8-week baseline), topic extraction, goal activity, and a short
narrative. Deterministic aggregation; the narrative is an injected ``llm_fn`` with a grounded
factual fallback. Below the minimum-session threshold it flags insufficient data and never
fabricates (§11, §13.3).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Callable, Optional

from backend.layer10_longitudinal.schemas import (
    NarrativeMoment,
    WeeklyEmotionalSummary,
    WeeklyProgressMetrics,
    WeeklySummary,
)

_MIN_SESSIONS = 2
_DELTA = 0.10


def aggregate_session_stats(sessions: list, week_start: date, week_end: date) -> dict:
    in_week = [s for s in sessions if week_start <= s.date <= week_end]
    dates = sorted(s.date for s in in_week)
    longest_gap = 0.0
    for a, b in zip(dates, dates[1:]):
        longest_gap = max(longest_gap, (b - a).days)
    return {
        "count": len(in_week),
        "dates": dates,
        "total_duration": sum(s.duration_mins for s in in_week),
        "longest_gap": float(longest_gap),
    }


def extract_weekly_topics(episodic_records: list, top_n: int = 5) -> list[str]:
    """Top conversation topics by frequency over the week (architecture doc §4.3 step 3)."""
    counts: dict[str, int] = {}
    order: list[str] = []
    for e in episodic_records:
        for t in e.topics:
            if t not in counts:
                order.append(t)
            counts[t] = counts.get(t, 0) + 1
    # Sort by frequency desc, stable by first-appearance for ties.
    return sorted(order, key=lambda t: (-counts[t], order.index(t)))[:top_n]


def build_weekly_emotional_summary(
    records: list, baseline_records: Optional[list] = None, prev_week=None,
) -> WeeklyEmotionalSummary:
    if not records:
        return WeeklyEmotionalSummary()
    valences = [r.valence for r in sorted(records, key=lambda r: r.date)]
    avg_v = sum(valences) / len(valences)
    avg_a = sum(r.arousal for r in records) / len(records)
    rng = max(valences) - min(valences)

    counts: dict[str, int] = {}
    for r in records:
        counts[r.primary_emotion] = counts.get(r.primary_emotion, 0) + 1
    dominant = max(counts, key=counts.get)

    delta = valences[-1] - valences[0]
    if rng > 0.9:
        trajectory = "volatile"
    elif delta > 0.15:
        trajectory = "improving"
    elif delta < -0.15:
        trajectory = "declining"
    else:
        trajectory = "stable"

    compared_prev = "not_enough_data"
    if prev_week is not None and getattr(prev_week, "emotional_summary", None) is not None:
        prev_v = prev_week.emotional_summary.avg_valence
        compared_prev = ("better" if avg_v > prev_v + _DELTA
                         else "worse" if avg_v < prev_v - _DELTA else "similar")

    compared_base = "at_baseline"
    if baseline_records:
        base = sum(r.valence for r in baseline_records) / len(baseline_records)
        compared_base = ("above_baseline" if avg_v > base + _DELTA
                         else "below_baseline" if avg_v < base - _DELTA else "at_baseline")

    return WeeklyEmotionalSummary(
        avg_valence=avg_v, avg_arousal=avg_a, dominant_emotion=dominant, emotional_range=rng,
        high_intensity_sessions=sum(1 for r in records if r.emotional_intensity > 0.70),
        trajectory=trajectory, compared_to_previous_week=compared_prev,
        compared_to_baseline=compared_base)


def compute_weekly_progress_metrics(sessions: list, goals: list, episodes: list) -> WeeklyProgressMetrics:
    n = len(sessions) or 1
    return WeeklyProgressMetrics(
        session_frequency=float(len(sessions)),
        avg_message_length_user=sum(s.user_message_length for s in sessions) / n,
        self_disclosure_events=sum(s.self_disclosure_events for s in sessions),
        crisis_events=sum(1 for s in sessions if s.crisis_mode_active))


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


def generate_weekly_summary(
    user_id: str,
    week_start: date,
    week_end: date,
    episodic_records: list,
    emotional_records: list,
    sessions: list,
    goals: Optional[list] = None,
    previous_week_summary=None,
    baseline_records: Optional[list] = None,
    llm_fn: Optional[Callable[[str], object]] = None,
    now: Optional[datetime] = None,
) -> WeeklySummary:
    """Assemble the week's synthesized summary (architecture doc §4.3)."""
    now = now or datetime.utcnow()
    goals = goals or []
    stats = aggregate_session_stats(sessions, week_start, week_end)
    week_emo = [r for r in emotional_records if week_start <= r.date <= week_end]
    week_eps = [e for e in episodic_records if week_start <= e.date <= week_end]

    emotional_summary = build_weekly_emotional_summary(
        week_emo, baseline_records=baseline_records, prev_week=previous_week_summary)
    topics = extract_weekly_topics(week_eps)
    most_significant = max(week_eps, key=lambda e: e.importance_score, default=None)
    most_moment = None
    if most_significant is not None:
        most_moment = NarrativeMoment(
            date=most_significant.date, title=most_significant.title,
            episode_ids=[most_significant.episode_id],
            significance_score=most_significant.importance_score)

    enough = stats["count"] >= _MIN_SESSIONS

    # Narrative: LLM if available and enough data; otherwise grounded fallback.
    narrative, standout = "", None
    if enough and llm_fn is not None:
        try:
            data = _coerce(llm_fn(f"Summarize the week of {week_start} for user {user_id}. "
                                  f"Topics: {topics}. Sessions: {stats['count']}."))
        except Exception:
            data = None
        if data is not None:
            narrative = data.get("summary", "")
            standout = data.get("standout")
    if not narrative:
        narrative = (f"{stats['count']} session(s) this week; "
                     f"top topics: {', '.join(topics) if topics else 'none recorded'}.")

    return WeeklySummary(
        user_id=user_id, week_start_date=week_start, week_end_date=week_end, generated_at=now,
        session_count=stats["count"], total_conversation_duration_mins=stats["total_duration"],
        session_dates=stats["dates"], longest_gap_in_week_days=stats["longest_gap"],
        emotional_summary=emotional_summary, most_emotionally_significant_moment=most_moment,
        primary_topics=topics, dominant_theme=topics[0] if topics else "",
        week_narrative=narrative, emotional_trajectory_this_week=emotional_summary.trajectory,
        standout_observation=standout,
        progress_metrics=compute_weekly_progress_metrics(sessions, goals, week_eps),
        minimum_data_threshold_met=enough)
