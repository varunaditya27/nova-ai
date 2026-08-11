"""SC-4 comparison + parsing helpers (architecture doc §6.3). Split out of ``retrospective.py``."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from backend.layer10_longitudinal.schemas import ThenVsNow


def as_date(value) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


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


def nearest_weekly_summary(weekly_summaries: list, reference_date: date):
    """The weekly summary whose week is nearest to reference_date, or None (§6.3)."""
    if not weekly_summaries:
        return None
    return min(weekly_summaries, key=lambda w: abs((w.week_start_date - reference_date).days))


def coerce_llm_json(raw) -> Optional[dict]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None
    return None
