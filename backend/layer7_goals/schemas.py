"""Schemas for Layer 7 — Goals & Accountability Engine.

Layer 7 tracks meaningful, self-directed intentions the user mentions in conversation —
not a task manager, but the engine that holds the thread of a person's goals across
sessions and is genuinely invested in where they're going (architecture doc §1).

Five sub-components:

    SC-1 Goal Extractor                  (goal_extractor.py)
    SC-2 Goal Store                      (goal_store.py)
    SC-3 Progress Monitor                (progress_monitor.py)
    SC-4 Accountability Response Modifier (accountability_modifier.py)
    SC-5 Goal Decomposer                 (goal_decomposer.py)
    orchestrator                         (engine.py) → Layer7Output

Design commitments encoded here (architecture doc §11):
- Goals are inferred, never solicited.
- Progress is narrated, never scored to the user (scores are internal-only).
- Goals yield to the present moment (Layer 3 emotion, Layer 5 social) on conflict.
- Accountability is holding the thread, never pressure.
- Abandonment is valid data — archived with history, never re-surfaced unprompted.

Pure stdlib (dataclasses + str-Enum) so the layer runs and tests offline. The LLM calls
(SC-1 extraction, SC-3 deep inference, SC-5 decomposition) and embedding similarity are
injected as callables. The Layer 6 handoff reuses Layer 6's intake contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


# ════════════════════════════════════════════════════════════════════════════
# SC-1 signal strength
# ════════════════════════════════════════════════════════════════════════════
class GoalSignalStrength(str, Enum):
    EXPLICIT_STATED = "explicit_stated"
    IMPLICIT_ASPIRED = "implicit_aspired"
    REPEATED_THEME = "repeated_theme"
    ABANDONED_REVISIT = "abandoned_revisit"


# ════════════════════════════════════════════════════════════════════════════
# SC-2 goal enums
# ════════════════════════════════════════════════════════════════════════════
class GoalDomain(str, Enum):
    HEALTH = "health"
    CAREER = "career"
    RELATIONSHIPS = "relationships"
    LEARNING = "learning"
    FINANCE = "finance"
    CREATIVITY = "creativity"
    PERSONAL_GROWTH = "personal_growth"
    OTHER = "other"


class GoalDirection(str, Enum):
    ACHIEVE_OUTCOME = "achieve_outcome"
    BUILD_HABIT = "build_habit"
    STOP_BEHAVIOR = "stop_behavior"
    MAINTAIN_STATE = "maintain_state"
    DEVELOP_SKILL = "develop_skill"


class GoalStatus(str, Enum):
    TENTATIVE = "tentative"
    ACTIVE = "active"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    PAUSED = "paused"
    ABANDONED = "abandoned"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GoalSignalEventType(str, Enum):
    CREATED = "created"
    REAFFIRMED = "reaffirmed"
    PROGRESS_POSITIVE = "progress_positive"
    PROGRESS_NEGATIVE = "progress_negative"
    OBSTACLE_MENTIONED = "obstacle_mentioned"
    STRATEGY_MENTIONED = "strategy_mentioned"
    MOTIVATION_EXPRESSED = "motivation_expressed"
    DEADLINE_UPDATED = "deadline_updated"
    METRIC_UPDATED = "metric_updated"
    STATUS_CHANGED = "status_changed"
    MILESTONE_REACHED = "milestone_reached"
    MILESTONE_MISSED = "milestone_missed"
    HABIT_CHECKED = "habit_checked"
    ABANDONED = "abandoned"
    COMPLETED = "completed"
    PROACTIVE_SENT = "proactive_sent"
    PROACTIVE_RESPONDED = "proactive_responded"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    REACHED = "reached"
    MISSED = "missed"
    DEFERRED = "deferred"


class HabitFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    WEEKDAYS = "weekdays"
    CUSTOM = "custom"


# ════════════════════════════════════════════════════════════════════════════
# SC-3 / SC-4 enums
# ════════════════════════════════════════════════════════════════════════════
class ProgressSignalType(str, Enum):
    PROGRESS_POSITIVE = "progress_positive"
    PROGRESS_NEGATIVE = "progress_negative"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalReferenceType(str, Enum):
    ACKNOWLEDGE_PROGRESS = "acknowledge_progress"
    ACKNOWLEDGE_SETBACK = "acknowledge_setback"
    CELEBRATE_COMPLETION = "celebrate_completion"
    CONNECT_TOPIC = "connect_topic"
    GENTLE_CHECK = "gentle_check"
    NONE = "none"


class GoalReferencePosition(str, Enum):
    OPENING = "opening"
    BODY = "body"
    CLOSING = "closing"
    NONE = "none"


# ════════════════════════════════════════════════════════════════════════════
# SC-2 Milestone / Habit
# ════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════
# SC-2 GoalSignalEvent
# ════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════
# SC-2 Goal
# ════════════════════════════════════════════════════════════════════════════
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
    progress_score: float = 0.0
    progress_trend: str = "unknown"          # improving | stable | declining | unknown
    momentum_score: float = 0.0
    confidence_at_creation: float = 0.0

    has_metric: bool = False
    metric_description: Optional[str] = None
    metric_unit: Optional[str] = None
    metric_target: Optional[float] = None
    metric_current: Optional[float] = None
    metric_at_creation: Optional[float] = None

    emotional_weight: float = 0.0
    emotional_weight_updated_at: Optional[datetime] = None

    milestones: list = field(default_factory=list)   # list[Milestone]
    habits: list = field(default_factory=list)        # list[Habit]
    signal_events: list = field(default_factory=list) # list[GoalSignalEvent]

    proactive_items_created: list = field(default_factory=list)
    last_proactive_sent_at: Optional[datetime] = None


# ════════════════════════════════════════════════════════════════════════════
# SC-1 extraction result
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class GoalExtractionResult:
    extraction_timestamp: Optional[datetime] = None
    message_id: str = ""
    goal_detected: bool = False
    is_update: bool = False
    goal_id_if_update: Optional[str] = None
    update_type: Optional[str] = None
    update_description: Optional[str] = None
    new_goal_data: Optional[dict] = None
    confidence: float = 0.0
    was_duplicate: bool = False
    matched_goal_id: Optional[str] = None
    processing_time_ms: int = 0


# ════════════════════════════════════════════════════════════════════════════
# SC-3 progress classification + state change
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class ProgressSignalClassification:
    signal_type: str = ProgressSignalType.PROGRESS_POSITIVE.value
    confidence: float = 0.0
    evidence: str = ""


@dataclass
class GoalStateChange:
    goal_id: str = ""
    new_status: str = ""
    reason: str = ""


# ════════════════════════════════════════════════════════════════════════════
# SC-4 retrieval + context packet
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class RelevantGoal:
    goal: Goal = field(default_factory=Goal)
    relevance_score: float = 0.0


@dataclass
class GoalContextPacket:
    relevant_goals: list = field(default_factory=list)   # list[RelevantGoal]

    should_reference_goal: bool = False
    reference_type: str = GoalReferenceType.NONE.value
    primary_goal: Optional[Goal] = None

    progress_signal_detected: bool = False
    progress_signal_type: Optional[str] = None
    progress_signal_evidence: Optional[str] = None

    new_goal_pending: Optional[GoalExtractionResult] = None

    response_instruction: Optional[str] = None
    tone_instruction: Optional[str] = None
    max_goal_reference_chars: int = 0
    goal_reference_position: str = GoalReferencePosition.NONE.value


# ════════════════════════════════════════════════════════════════════════════
# §8 outputs
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class GoalUWMUpdate:
    user_id: str = ""
    event_type: str = "goal_created"
    goal_id: str = ""
    goal_title: str = ""
    goal_domain: str = GoalDomain.OTHER.value
    summary: str = ""
    emotional_significance: float = 0.0
    timestamp: Optional[datetime] = None


@dataclass
class Layer7Output:
    goal_context_packet: GoalContextPacket = field(default_factory=GoalContextPacket)
    new_goals_created: list = field(default_factory=list)
    goals_updated: list = field(default_factory=list)

    proactive_items_created: list = field(default_factory=list)
    layer2_uwm_update: Optional[GoalUWMUpdate] = None

    stale_goals_updated: list = field(default_factory=list)
    milestones_decomposed: list = field(default_factory=list)

    cycle_timestamp: Optional[datetime] = None
    processing_time_ms: int = 0
