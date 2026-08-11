"""SC-4 retrieval + context packet, and the §8 Layer 7 output contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import GoalDomain, GoalReferencePosition, GoalReferenceType
from .extraction import GoalExtractionResult
from .goal import Goal


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
