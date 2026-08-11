"""SC-1 Life Narrative Engine schemas (architecture doc §3.2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class NarrativeRole(str, Enum):
    TURNING_POINT = "turning_point"
    ACHIEVEMENT = "achievement"
    SETBACK = "setback"
    DISCLOSURE = "disclosure"
    DECISION = "decision"
    REALIZATION = "realization"
    CONNECTION = "connection"


@dataclass
class EmotionalArcSummary:
    opening_valence: float = 0.0
    closing_valence: float = 0.0
    dominant_emotion: str = "neutral"
    emotional_range: float = 0.0
    trajectory: str = "mixed"        # improving|declining|stable_positive|stable_negative|
                                     # volatile|recovering|mixed
    notable_peaks: list = field(default_factory=list)    # (date, valence)
    notable_troughs: list = field(default_factory=list)


@dataclass
class NarrativeMoment:
    date: date
    title: str
    moment_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    episode_ids: list = field(default_factory=list)
    significance_score: float = 0.0
    narrative_role: str = NarrativeRole.REALIZATION.value
    reflection_prompt: Optional[str] = None


@dataclass
class LifeEvent:
    event_id: str
    user_id: str
    title: str
    category: str                    # career_transition|educational_transition|relational_major|
                                     # geographic_relocation|major_loss|health_major|other
    event_date: date
    significance_score: float = 0.5
    detected_at: Optional[datetime] = None
    associated_goal_id: Optional[str] = None
    description: Optional[str] = None


@dataclass
class LifeChapter:
    title: str
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    chapter_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    primary_theme: str = ""
    secondary_themes: list = field(default_factory=list)
    opening_context: str = ""
    defining_moments: list[NarrativeMoment] = field(default_factory=list)
    emotional_arc: Optional[EmotionalArcSummary] = None
    goals_active: list = field(default_factory=list)
    goals_resolved: list = field(default_factory=list)
    life_events: list = field(default_factory=list)
    growth_observed: list = field(default_factory=list)
    narrative_summary: str = ""
    synthesis_version: int = 0
    last_synthesized_at: Optional[datetime] = None


@dataclass
class NarrativeArc:
    user_id: str
    arc_start_date: date
    chapters: list[LifeChapter] = field(default_factory=list)
    current_chapter: Optional[LifeChapter] = None
    overall_themes: list = field(default_factory=list)
    running_growth_narrative: str = ""
    narrative_version: int = 0
    last_full_synthesis_at: Optional[datetime] = None


@dataclass
class ChapterSynthesis:
    narrative_summary: str = ""
    primary_theme: str = ""
    secondary_themes: list = field(default_factory=list)
    growth_observed: list = field(default_factory=list)
    revised_title: str = ""
