"""SC-3 Progress & Pattern Tracker schemas (architecture doc §5.2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class PatternType(str, Enum):
    EMOTIONAL_CYCLE = "emotional_cycle"
    BEHAVIORAL_AVOIDANCE = "behavioral_avoidance"
    POSITIVE_HABIT = "positive_habit"
    NEGATIVE_HABIT = "negative_habit"
    ENERGY_RHYTHM = "energy_rhythm"
    TOPIC_RECURRENCE = "topic_recurrence"


@dataclass
class BehavioralPattern:
    description: str
    pattern_type: str
    first_detected_date: date
    last_observed_date: date
    confidence: float = 0.0
    occurrence_count: int = 0
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    associated_goal_ids: list = field(default_factory=list)


@dataclass
class LifeDomainBalance:
    domain_weights: dict = field(default_factory=dict)
    dominant_domain: str = ""
    neglected_domains: list = field(default_factory=list)
    balance_score: float = 0.0
    balance_trend: str = "stable"    # concentrating|diversifying|stable


@dataclass
class ProgressSnapshot:
    """A compact longitudinal progress record (subset of the doc's full dimension set)."""
    user_id: str
    as_of_date: date
    snapshot_version: int = 0
    avg_valence_4w: float = 0.0
    avg_valence_12w: float = 0.0
    valence_trend_short: str = "stable"
    high_intensity_frequency: float = 0.0
    crisis_event_frequency: float = 0.0
    resilience_score: float = 0.0
    total_goals_lifetime: int = 0
    goals_achieved_lifetime: int = 0
    goals_abandoned_lifetime: int = 0
    achievement_rate_lifetime: float = 0.0
    avg_sessions_per_week_4w: float = 0.0
    domain_balance: Optional[LifeDomainBalance] = None
    active_patterns: list = field(default_factory=list)
