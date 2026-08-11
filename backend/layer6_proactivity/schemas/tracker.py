"""SC-5 ResponseClassification, §10 user preferences, and the §8 ProactiveEngineOutput
(Layer 6's output contract)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import ResponseType
from .generator import ProactiveDeliveryPayload
from .item import ProactiveItem


@dataclass
class ResponseClassification:
    responded: bool = False
    response_type: str = ResponseType.IGNORED.value
    engagement_score: float = 0.0
    response_valence: Optional[float] = None
    message_id: Optional[str] = None


@dataclass
class ProactivePreferences:
    proactive_all_enabled: bool = True
    proactive_thread_follow_up_enabled: bool = True
    proactive_emotional_check_in_enabled: bool = True
    proactive_wellbeing_check_enabled: bool = True
    proactive_silence_break_enabled: bool = False   # opt-in
    proactive_goal_check_in_enabled: bool = True
    proactive_social_pattern_coaching_enabled: bool = True
    proactive_relationship_check_in_enabled: bool = True

    preferred_send_hours_start: int = 9
    preferred_send_hours_end: int = 21
    quiet_days: list[int] = field(default_factory=list)
    max_proactive_per_week: int = 3


@dataclass
class ProactiveEngineOutput:
    messages_sent: list[ProactiveDeliveryPayload] = field(default_factory=list)
    messages_deferred: list[tuple] = field(default_factory=list)        # (item_id, reason)
    messages_suppressed: list[tuple] = field(default_factory=list)      # (item_id, reason)

    queue_size: int = 0
    highest_priority_item: Optional[ProactiveItem] = None
    next_evaluation_at: Optional[datetime] = None

    responses_received: list[ResponseClassification] = field(default_factory=list)
    preference_updates: dict = field(default_factory=dict)

    cycle_timestamp: Optional[datetime] = None
    total_items_evaluated: int = 0
    gate_decisions: list[tuple] = field(default_factory=list)           # (item_id, reason)
