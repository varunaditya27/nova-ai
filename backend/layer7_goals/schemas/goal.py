"""SC-2 Milestone, Habit, GoalSignalEvent, and Goal (architecture doc §4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .enums import (
    GoalDirection,
    GoalDomain,
    GoalSignalEventType,
    GoalSignalStrength,
    GoalStatus,
    HabitFrequency,
    MilestoneStatus,
)


@dataclass
class Milestone:
    milestone_id: str = field(default_factory=lambda: str(uuid4()))
    goal_id: str = ""
    title: str = ""
    description: str = ""
    target_date: Optional[datetime] = None
    status: str = MilestoneStatus.PENDING.value
    created_at: Optional[datetime] = None
    created_by: str = "system"               # "system" | "user"
    reached_at: Optional[datetime] = None
    evidence: Optional[str] = None
    progress_weight: float = 0.25


@dataclass
class Habit:
    habit_id: str = field(default_factory=lambda: str(uuid4()))
    goal_id: str = ""
    title: str = ""
    description: str = ""
    frequency: str = HabitFrequency.WEEKLY.value
    target_count_per_period: int = 1
    current_streak: int = 0
    best_streak: int = 0
    total_check_ins: int = 0
    last_checked_in: Optional[datetime] = None
    status: str = "active"                    # "active" | "paused" | "abandoned"
    created_at: Optional[datetime] = None


@dataclass
class GoalSignalEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    goal_id: str = ""
    event_type: str = GoalSignalEventType.CREATED.value
    timestamp: Optional[datetime] = None
    session_id: str = ""
    evidence_text: str = ""
    inferred: bool = False
    confidence: float = 0.0
    progress_delta: Optional[float] = None
    status_before: Optional[str] = None
    status_after: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Goal:
    goal_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    title: str = ""
    title_embedding: Optional[list] = None
    raw_statement: str = ""
    domain: str = GoalDomain.OTHER.value
    direction: str = GoalDirection.ACHIEVE_OUTCOME.value

    description: str = ""
    outcome_definition: Optional[str] = None
    motivation_notes: Optional[str] = None
    obstacles_noted: list = field(default_factory=list)
    strategies_noted: list = field(default_factory=list)
    prior_attempts: int = 0

    created_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    deadline_description: Optional[str] = None
    deadline_is_inferred: bool = False
    last_mentioned_at: Optional[datetime] = None
    last_progress_at: Optional[datetime] = None
    last_setback_at: Optional[datetime] = None
    first_active_at: Optional[datetime] = None

    status: str = GoalStatus.TENTATIVE.value
    status_changed_at: Optional[datetime] = None
    progress_score: float = 0.0
    progress_trend: str = "unknown"          # improving | stable | declining | unknown
    momentum_score: float = 0.0
    confidence_at_creation: float = 0.0
    signal_strength: str = GoalSignalStrength.EXPLICIT_STATED.value

    has_metric: bool = False
    metric_description: Optional[str] = None
    metric_unit: Optional[str] = None
    metric_target: Optional[float] = None
    metric_current: Optional[float] = None
    metric_at_creation: Optional[float] = None

    emotional_weight: float = 0.0
    emotional_weight_updated_at: Optional[datetime] = None

    milestones: list[Milestone] = field(default_factory=list)
    habits: list[Habit] = field(default_factory=list)
    signal_events: list[GoalSignalEvent] = field(default_factory=list)

    proactive_items_created: list = field(default_factory=list)
    last_proactive_sent_at: Optional[datetime] = None
