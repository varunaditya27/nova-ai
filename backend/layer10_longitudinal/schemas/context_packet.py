"""Layer 10 output contract — Layer10ContextPacket (architecture doc §8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from backend.layer10_longitudinal.schemas.narrative import LifeEvent
from backend.layer10_longitudinal.schemas.retrospective import RetrospectivePacket
from backend.layer10_longitudinal.schemas.weekly import WeeklySummary


@dataclass
class Layer10ContextPacket:
    user_id: str
    generated_at: Optional[datetime] = None
    current_chapter_summary: str = ""
    current_chapter_theme: str = ""
    running_growth_narrative: str = ""
    days_since_nova_relationship_started: int = 0
    emotional_trend_recent: str = ""
    primary_active_goals: list = field(default_factory=list)
    dominant_life_domain: str = ""
    pending_retrospectives: list = field(default_factory=list)
    highest_priority_retrospective: Optional[RetrospectivePacket] = None
    active_behavioral_patterns: list = field(default_factory=list)
    current_week_summary: Optional[WeeklySummary] = None
    last_week_summary: Optional[WeeklySummary] = None
    upcoming_goal_deadlines: list = field(default_factory=list)
    recent_life_event: Optional[LifeEvent] = None
    minimum_data_threshold_met: bool = True
