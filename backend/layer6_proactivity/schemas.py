"""Schemas for Layer 6 — Proactive Engagement Engine.

Layer 6 is the first layer that operates *without being triggered by the user*. It decides
when Nova reaches out first, what it says, and whether the timing/content is appropriate
(architecture doc §1). It runs as a background loop, independent of the message pipeline,
and defaults overwhelmingly to silence.

Five sub-components:

    SC-1 Proactive Queue Manager     (queue_manager.py)
    SC-2 Initiative Classifier       (initiative_classifier.py)
    SC-3 Timing & Delivery Gate      (timing_gate.py)
    SC-4 Proactive Message Generator (message_generator.py)
    SC-5 Response Tracker            (response_tracker.py)
    intake contracts (§9)            (intake.py)
    orchestrator                     (engine.py) → ProactiveEngineOutput

Pure stdlib (dataclasses + str-Enum) so the entire layer runs and tests offline. The single
LLM call (SC-4) is injected as a callable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


# ════════════════════════════════════════════════════════════════════════════
# SC-1 enums
# ════════════════════════════════════════════════════════════════════════════
class ProactiveItemType(str, Enum):
    """Every kind of outreach Layer 6 might send (architecture doc §3.2)."""

    # Narrative thread follow-ups (Layer 1)
    THREAD_FOLLOW_UP = "thread_follow_up"
    THREAD_EXPIRY_CHECK = "thread_expiry_check"
    THREAD_ANNIVERSARY = "thread_anniversary"

    # Emotional continuity (Layer 2/3)
    EMOTIONAL_CHECK_IN = "emotional_check_in"
    SILENCE_BREAK = "silence_break"
    POSITIVE_REINFORCEMENT = "positive_reinforcement"

    # Social coaching (Layer 5)
    SOCIAL_PATTERN_COACHING = "social_pattern_coaching"
    RELATIONSHIP_CHECK_IN = "relationship_check_in"
    CONFLICT_RESOLUTION_CHECK = "conflict_resolution_check"

    # Goal-related (Layer 7)
    GOAL_CHECK_IN = "goal_check_in"
    GOAL_ENCOURAGEMENT = "goal_encouragement"
    GOAL_CELEBRATION = "goal_celebration"

    # Life context (UWM)
    UPCOMING_DATE_REMINDER = "upcoming_date_reminder"
    RECURRING_CONCERN_CHECK = "recurring_concern_check"
    WELLBEING_CHECK = "wellbeing_check"


class ItemStatus(str, Enum):
    PENDING = "pending"
    DEFERRED = "deferred"
    APPROVED = "approved"
    SENT = "sent"
    RESPONDED = "responded"
    IGNORED = "ignored"
    EXPIRED = "expired"
    SUPPRESSED = "suppressed"


# ════════════════════════════════════════════════════════════════════════════
# SC-2 enums
# ════════════════════════════════════════════════════════════════════════════
class InitiativeType(str, Enum):
    CARING_CHECK_IN = "caring_check_in"
    CURIOUS_FOLLOW_UP = "curious_follow_up"
    CONCERNED_CHECK_IN = "concerned_check_in"
    CELEBRATORY_FOLLOW_UP = "celebratory_follow_up"
    GENTLE_NUDGE = "gentle_nudge"
    RECONNECTION_OPENER = "reconnection_opener"
    ANNIVERSARY_RECALL = "anniversary_recall"


class EmotionalRegister(str, Enum):
    WARM_CASUAL = "warm_casual"
    WARM_CAREFUL = "warm_careful"
    WARM_DIRECT = "warm_direct"
    WARM_ENERGETIC = "warm_energetic"
    WARM_NEUTRAL = "warm_neutral"
    WARM_LIGHT = "warm_light"


class ContentFraming(str, Enum):
    OPEN_ENDED = "open_ended"
    EVENT_SPECIFIC = "event_specific"
    FEELING_FOCUSED = "feeling_focused"
    LIGHT_TOUCH = "light_touch"
    INVITATIONAL = "invitational"


class ReferenceDepth(str, Enum):
    NONE = "none"
    MINIMAL = "minimal"
    VAGUE = "vague"
    SPECIFIC = "specific"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuestionType(str, Enum):
    OPEN = "open"
    SPECIFIC = "specific"
    CHECKING_IN = "checking_in"
    NONE = "none"


# ════════════════════════════════════════════════════════════════════════════
# SC-3 / SC-4 / SC-5 enums
# ════════════════════════════════════════════════════════════════════════════
class GateAction(str, Enum):
    SEND_NOW = "send_now"
    DEFER = "defer"
    SUPPRESS = "suppress"


class DeliveryChannel(str, Enum):
    PUSH_NOTIFICATION = "push_notification"
    IN_APP_MESSAGE = "in_app_message"
    SCHEDULED_WHATSAPP = "scheduled_whatsapp"


class ResponseType(str, Enum):
    IMMEDIATE = "immediate"
    QUICK = "quick"
    SAME_DAY = "same_day"
    DELAYED = "delayed"
    IGNORED = "ignored"


# ════════════════════════════════════════════════════════════════════════════
# SC-1 ProactiveItem
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class ProactiveItem:
    item_id: str = field(default_factory=lambda: str(uuid4()))
    item_type: str = ProactiveItemType.THREAD_FOLLOW_UP.value
    source_layer: str = "layer1"

    # Content basis
    content_basis: str = ""
    content_basis_valence: Optional[float] = None
    source_memory_ids: list[str] = field(default_factory=list)
    source_event_ids: list[str] = field(default_factory=list)
    source_goal_id: Optional[str] = None

    # People involved
    person_id: Optional[str] = None
    person_display_name: Optional[str] = None

    # Priority
    base_priority: float = 0.5
    current_priority: float = 0.5
    priority_last_updated: Optional[datetime] = None

    # Timing
    earliest_send_time: Optional[datetime] = None
    optimal_send_window: Optional[tuple] = None    # (start, end)
    expiry_time: Optional[datetime] = None

    # Lifecycle
    status: str = ItemStatus.PENDING.value
    created_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    send_attempt_count: int = 0

    # Response tracking
    user_response_valence: Optional[float] = None
    user_engaged: Optional[bool] = None


# ════════════════════════════════════════════════════════════════════════════
# SC-2 ClassifiedInitiative
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class ClassifiedInitiative:
    initiative_type: str = InitiativeType.CARING_CHECK_IN.value
    emotional_register: str = EmotionalRegister.WARM_CASUAL.value
    content_framing: str = ContentFraming.OPEN_ENDED.value
    reference_depth: str = ReferenceDepth.VAGUE.value
    urgency: str = Urgency.LOW.value
    opening_posture: str = "soft_check"
    max_length_chars: int = 200
    include_question: bool = True
    question_type: str = QuestionType.OPEN.value


# ════════════════════════════════════════════════════════════════════════════
# SC-3 GateDecision + UserTimingContext
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class GateDecision:
    action: str = GateAction.SEND_NOW.value
    reason: str = ""
    retry_after: Optional[datetime] = None
    approved_at: Optional[datetime] = None


@dataclass
class UserTimingContext:
    circadian_band: str = "afternoon"
    user_timezone: str = "UTC"
    minutes_since_last_message: int = 999
    hours_since_last_proactive_message: float = 9999.0
    last_proactive_sent_at: Optional[datetime] = None
    proactive_messages_sent_today: int = 0

    # Emotional state
    bes_trend: str = "stable"
    last_session_crisis_flag: bool = False
    last_session_end_valence: float = 0.0

    # Relationship state
    relationship_stage: str = "developing"
    tie_strength: float = 0.5

    # User preferences
    user_preferences: dict = field(default_factory=dict)
    is_in_quiet_period: bool = False
    quiet_period_end: Optional[datetime] = None

    # Session state
    user_is_currently_active: bool = False


# ════════════════════════════════════════════════════════════════════════════
# SC-4 ProactiveContext + delivery + validation
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class ProactiveContext:
    source_memory_summaries: list[str] = field(default_factory=list)
    source_thread_summary: Optional[str] = None
    source_event_summary: Optional[str] = None
    source_goal_summary: Optional[str] = None

    user_name_if_known: Optional[str] = None
    current_life_context: str = ""
    bes_trend_description: str = ""

    persona_instruction: str = ""
    relationship_stage: str = "developing"
    voice_parameters_summary: str = ""
    prior_proactive_topics: list[str] = field(default_factory=list)


@dataclass
class ProactiveValidationResult:
    passed: bool = True
    issue: Optional[str] = None
    action: Optional[str] = None


@dataclass
class ProactiveDeliveryPayload:
    user_id: str = ""
    message_text: str = ""
    item_id: str = ""
    delivery_channel: str = DeliveryChannel.PUSH_NOTIFICATION.value
    delivery_channel_priority: list[str] = field(default_factory=list)
    send_at: Optional[datetime] = None
    expiry_after_send: int = 0
    allow_reply: bool = True
    tracking_enabled: bool = True


# ════════════════════════════════════════════════════════════════════════════
# SC-5 ResponseClassification
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class ResponseClassification:
    responded: bool = False
    response_type: str = ResponseType.IGNORED.value
    engagement_score: float = 0.0
    response_valence: Optional[float] = None
    message_id: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# §10 User preferences
# ════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════
# §8 ProactiveEngineOutput — Layer 6 output
# ════════════════════════════════════════════════════════════════════════════
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
