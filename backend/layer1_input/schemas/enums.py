"""Enumerations for Layer 1 — Input Perception (architecture doc §3, §4, §5, §6)."""

from __future__ import annotations

from enum import Enum


class CircadianBand(str, Enum):
    """Six wall-clock bands (architecture doc §3.2). Fully partitions 0–24h."""

    LATE_NIGHT = "late_night"        # 23:00–03:00
    EARLY_MORNING = "early_morning"  # 03:00–06:00
    MORNING = "morning"              # 06:00–12:00
    AFTERNOON = "afternoon"          # 12:00–17:00
    EVENING = "evening"              # 17:00–21:00
    NIGHT = "night"                  # 21:00–23:00


class GapCategory(str, Enum):
    """Seven session-gap buckets (architecture doc §3.3)."""

    SAME_SESSION = "same_session"            # 0–30 min
    SHORT_BREAK = "short_break"              # 30 min–4 hrs
    SAME_DAY = "same_day"                    # 4–24 hrs
    FEW_DAYS = "few_days"                    # 1–3 days
    WEEK_OR_TWO = "week_or_two"              # 3–14 days
    LONG_ABSENCE = "long_absence"            # 14 days–3 months
    VERY_LONG_ABSENCE = "very_long_absence"  # 3+ months


class LatencySignal(str, Enum):
    """Response-latency interpretation labels (architecture doc §4.2)."""

    REACTIVE = "reactive"        # < 3 s
    QUICK = "quick"              # 3–15 s
    CONSIDERED = "considered"    # 15–60 s
    REFLECTIVE = "reflective"    # 1–5 min
    DELAYED = "delayed"          # 5–20 min
    BREAK = "break"              # > 20 min — triggers re-entry posture


class InitiationType(str, Enum):
    """Session-initiation categories (architecture doc §4.5)."""

    USER_INITIATED_COLD = "user_initiated_cold"
    USER_INITIATED_HOT = "user_initiated_hot"
    RESPONSE_TO_CHECKIN = "response_to_checkin"
    CONTINUATION = "continuation"


class ThreadStatus(str, Enum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    SNOOZED = "snoozed"


class ImportanceTier(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ThreadType(str, Enum):
    FUTURE_EVENT = "future_event"
    EMOTIONAL_SITUATION = "emotional_situation"
    INTENTION_COMMITMENT = "intention_commitment"
    CHRONIC_CONTEXT = "chronic_context"
    FACTUAL_PENDING = "factual_pending"


class AttachmentType(str, Enum):
    IMAGE = "image"
    VOICE = "voice"
    DOCUMENT = "document"
    LOCATION = "location"
    VIDEO = "video"
    REACTION = "reaction"
    FILE = "file"


class PrimaryModality(str, Enum):
    """Resolved modality of the inbound event (architecture doc §5.6).

    The ``*_UNPROCESSED`` / ``*_UNTRANSCRIBED`` values are degraded-mode fallbacks
    emitted when a normalizer backend fails or is unavailable (§11).
    """

    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    DOCUMENT = "document"
    LOCATION = "location"
    VIDEO = "video"
    REACTION = "reaction"
    MIXED = "mixed"
    IMAGE_UNPROCESSED = "image_unprocessed"
    VOICE_UNTRANSCRIBED = "voice_untranscribed"


class DocumentType(str, Enum):
    ACADEMIC = "academic"
    PROFESSIONAL = "professional"
    PERSONAL = "personal"
    TECHNICAL = "technical"
    UNKNOWN = "unknown"


class ProsodyDominantSignal(str, Enum):
    ANXIOUS = "anxious"
    DISTRESSED = "distressed"
    FLAT_AFFECT = "flat_affect"
    ANIMATED = "animated"
    FATIGUED = "fatigued"
    NEUTRAL = "neutral"
