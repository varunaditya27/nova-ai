"""Layer 10 engine — Layer10ContextPacket assembly (architecture doc §8).

Assembles the read-path context object Layer 10 provides to Layer 4 (long-term grounding) and
Layer 6 (surfacing decisions) at session start. In production this reads from pre-computed caches
(< 100ms, §12); here it composes the already-synthesized sub-component outputs. Every field is
defensive — missing inputs degrade to an empty-but-valid packet flagged as insufficient data,
never a crash (§11).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer10_longitudinal.schemas import Layer10ContextPacket

_TREND_PHRASES = {
    "improving": "improving recently",
    "declining": "declining recently",
    "stable": "holding steady recently",
}


def assemble_context_packet(
    user_id: str,
    narrative_arc=None,
    progress_snapshot=None,
    current_week_summary=None,
    last_week_summary=None,
    pending_retrospectives: Optional[list] = None,
    active_patterns: Optional[list] = None,
    recent_life_event=None,
    upcoming_goal_deadlines: Optional[list] = None,
    primary_active_goals: Optional[list] = None,
    days_since_started: int = 0,
    now: Optional[datetime] = None,
) -> Layer10ContextPacket:
    """Build the Layer10ContextPacket from synthesized sub-component outputs (doc §8)."""
    now = now or datetime.utcnow()

    # Narrative context from the current chapter.
    chapter_summary, chapter_theme, growth_narrative = "", "", ""
    if narrative_arc is not None:
        growth_narrative = getattr(narrative_arc, "running_growth_narrative", "") or ""
        current = getattr(narrative_arc, "current_chapter", None)
        if current is not None:
            chapter_summary = getattr(current, "narrative_summary", "") or ""
            chapter_theme = getattr(current, "primary_theme", "") or ""

    # Progress context.
    emotional_trend, dominant_domain = "", ""
    if progress_snapshot is not None:
        emotional_trend = _TREND_PHRASES.get(
            getattr(progress_snapshot, "valence_trend_short", "stable"), "")
        balance = getattr(progress_snapshot, "domain_balance", None)
        if balance is not None:
            dominant_domain = getattr(balance, "dominant_domain", "") or ""

    # Retrospectives — unsurfaced, sorted by priority desc.
    pending = [r for r in (pending_retrospectives or [])
               if not getattr(r, "has_been_surfaced", False)]
    pending.sort(key=lambda r: getattr(r, "surfacing_priority", 0.0), reverse=True)
    highest = pending[0] if pending else None

    has_data = narrative_arc is not None or progress_snapshot is not None \
        or current_week_summary is not None

    return Layer10ContextPacket(
        user_id=user_id, generated_at=now,
        current_chapter_summary=chapter_summary, current_chapter_theme=chapter_theme,
        running_growth_narrative=growth_narrative,
        days_since_nova_relationship_started=days_since_started,
        emotional_trend_recent=emotional_trend, primary_active_goals=primary_active_goals or [],
        dominant_life_domain=dominant_domain, pending_retrospectives=pending,
        highest_priority_retrospective=highest, active_behavioral_patterns=active_patterns or [],
        current_week_summary=current_week_summary, last_week_summary=last_week_summary,
        upcoming_goal_deadlines=upcoming_goal_deadlines or [], recent_life_event=recent_life_event,
        minimum_data_threshold_met=has_data)
