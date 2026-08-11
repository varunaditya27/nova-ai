"""Enumerations for Layer 6 — Proactive Engagement Engine."""

from __future__ import annotations

from enum import Enum


# ── SC-1 enums ───────────────────────────────────────────────────────────────
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

    # Longitudinal (Layer 10)
    BEHAVIORAL_PATTERN_SURFACING = "behavioral_pattern_surfacing"
    RETROSPECTIVE_REFLECTION = "retrospective_reflection"


class ItemStatus(str, Enum):
    PENDING = "pending"
    DEFERRED = "deferred"
    APPROVED = "approved"
    SENT = "sent"
    RESPONDED = "responded"
    IGNORED = "ignored"
    EXPIRED = "expired"
    SUPPRESSED = "suppressed"


# ── SC-2 enums ───────────────────────────────────────────────────────────────
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


# ── SC-3 / SC-4 / SC-5 enums ─────────────────────────────────────────────────
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
