"""SC-2 Weekly Summary schemas (architecture doc §4.2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from backend.layer10_longitudinal.schemas.narrative import NarrativeMoment


@dataclass
class WeeklyEmotionalSummary:
    avg_valence: float = 0.0
    avg_arousal: float = 0.0
    dominant_emotion: str = "neutral"
    emotional_range: float = 0.0
    high_intensity_sessions: int = 0
    trajectory: str = "stable"       # improving|declining|stable|volatile
    compared_to_previous_week: str = "not_enough_data"
    compared_to_baseline: str = "at_baseline"


@dataclass
class WeeklyProgressMetrics:
    session_frequency: float = 0.0
    avg_session_depth: float = 0.0
    goal_progress_velocity: float = 0.0
    new_goal_activation_count: int = 0
    goal_abandonment_count: int = 0
    avg_message_length_user: float = 0.0
    self_disclosure_events: int = 0
    crisis_events: int = 0


@dataclass
class WeeklySummary:
    user_id: str
    week_start_date: date
    week_end_date: date
    summary_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    generated_at: Optional[datetime] = None
    session_count: int = 0
    total_conversation_duration_mins: float = 0.0
    session_dates: list = field(default_factory=list)
    longest_gap_in_week_days: float = 0.0
    emotional_summary: Optional[WeeklyEmotionalSummary] = None
    most_emotionally_significant_moment: Optional[NarrativeMoment] = None
    primary_topics: list = field(default_factory=list)
    dominant_theme: str = ""
    new_topics_introduced: list = field(default_factory=list)
    goals_mentioned: list = field(default_factory=list)
    goals_progressed: list = field(default_factory=list)
    goals_stalled: list = field(default_factory=list)
    week_narrative: str = ""
    emotional_trajectory_this_week: str = "stable"
    standout_observation: Optional[str] = None
    progress_metrics: Optional[WeeklyProgressMetrics] = None
    minimum_data_threshold_met: bool = True
