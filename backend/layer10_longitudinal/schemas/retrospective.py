"""SC-4 Retrospective Engine schemas, incl. Year in Review (architecture doc §6.2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from backend.layer10_longitudinal.schemas.narrative import EmotionalArcSummary


class RetrospectiveType(str, Enum):
    ONE_WEEK_AGO = "one_week_ago"
    ONE_MONTH_AGO = "one_month_ago"
    THREE_MONTHS_AGO = "three_months_ago"
    SIX_MONTHS_AGO = "six_months_ago"
    ONE_YEAR_AGO = "one_year_ago"
    GOAL_ANNIVERSARY = "goal_anniversary"
    CHAPTER_CLOSE = "chapter_close"
    RELATIONSHIP_MILESTONE = "relationship_milestone"
    FIRST_YEAR_IN_REVIEW = "first_year_in_review"
    QUARTERLY_GROWTH = "quarterly_growth"
    PATTERN_SURFACING = "pattern_surfacing"


@dataclass
class ThenVsNow:
    then_primary_concern: str = ""
    now_primary_concern: str = ""
    then_emotional_state: str = ""
    now_emotional_state: str = ""
    then_active_goals: list = field(default_factory=list)
    now_active_goals: list = field(default_factory=list)
    key_change: str = ""


@dataclass
class RetrospectivePacket:
    user_id: str
    retrospective_type: str
    reference_date: date
    packet_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    generated_at: Optional[datetime] = None
    headline: str = ""
    narrative_reflection: str = ""
    then_vs_now: Optional[ThenVsNow] = None
    growth_highlights: list = field(default_factory=list)
    reflection_questions: list = field(default_factory=list)
    backing_episode_ids: list = field(default_factory=list)
    surfacing_priority: float = 0.0
    surfacing_window_days: int = 7
    has_been_surfaced: bool = False
    surfaced_at: Optional[datetime] = None
    user_engagement: Optional[str] = None


@dataclass
class YearInReview:
    user_id: str
    year: int
    chapter_count: int = 0
    total_sessions: int = 0
    goals_set: int = 0
    goals_achieved: int = 0
    goals_abandoned: int = 0
    goals_carrying_forward: int = 0
    emotional_arc: Optional[EmotionalArcSummary] = None
    defining_moments: list = field(default_factory=list)
    hardest_period_summary: Optional[str] = None
    best_period_summary: Optional[str] = None
    dominant_growth_theme: str = ""
    year_narrative: str = ""
