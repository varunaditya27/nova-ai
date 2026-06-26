"""Schemas for Layer 1 — Input Perception.

This module defines every data structure produced or consumed by Layer 1. They are the
formal contract handed to all downstream layers (see ``docs/layer-1-architecture.md`` §7.3).

Design principles (architecture doc §14):
  * Pure-Python / zero third-party dependencies — stdlib ``dataclasses`` + ``enum`` only.
  * Read-only contract objects. The pipeline builds an ``InputPerceptionPacket`` once and
    never mutates it afterwards.
  * Every field has an explicit default so a *partial* packet can always be emitted even
    when an optional sub-component (SC-3 / SC-4) did not fire (§7.3, §11 "always emit").

All enums subclass ``str`` so a packet field compares equal to its plain-string spelling
(``packet.circadian_band == "morning"``) while remaining type-checked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Callable, Optional
from uuid import UUID


# ────────────────────────────────────────────────────────────────────────────
# Enumerations
# ────────────────────────────────────────────────────────────────────────────
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


# ────────────────────────────────────────────────────────────────────────────
# Temporal sub-component types (SC-1)
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class NarrativeThread:
    """An open conversational loop awaiting follow-up (architecture doc §3.5)."""

    thread_id: UUID
    summary: str
    created_at: datetime
    follow_up_due_at: datetime
    status: ThreadStatus = ThreadStatus.UNRESOLVED
    emotional_weight: float = 0.0          # 0–1; influences surfacing priority
    importance_tier: ImportanceTier = ImportanceTier.MEDIUM
    thread_type: ThreadType = ThreadType.FACTUAL_PENDING
    snooze_until: Optional[datetime] = None
    source_session_id: Optional[UUID] = None


@dataclass
class UserTemporalProfile:
    """Per-user behavioral baseline for anomaly detection (architecture doc §3.4).

    Mirrors the spec field-for-field. Rolling latency / message-length / gap histories
    live in separate on-device history tables (§8) and are passed to the resolver as
    explicit parameters rather than embedded here.
    """

    user_id: UUID
    timezone_offset_hours: float = 0.0
    typical_bands: dict[str, float] = field(default_factory=dict)   # band → frequency (0–1)
    average_session_frequency_days: float = 0.0
    typical_session_duration_minutes: float = 0.0
    longest_historical_gap_days: float = 0.0
    last_session_end: Optional[datetime] = None
    total_sessions: int = 0
    relationship_age_days: int = 0
    per_band_circadian_prior: dict[str, float] = field(default_factory=dict)


# ────────────────────────────────────────────────────────────────────────────
# Multimodal sub-component types (SC-3)
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class DocumentSummary:
    """Normalized document representation (architecture doc §5.5)."""

    document_type: DocumentType = DocumentType.UNKNOWN
    title: Optional[str] = None
    extracted_text: str = ""                       # full text, up to 10,000 chars
    key_dates: list[str] = field(default_factory=list)
    key_entities: list[str] = field(default_factory=list)
    estimated_emotional_significance: float = 0.0  # 0–1


@dataclass
class ModalityContext:
    """Normalized representation of any non-text input (architecture doc §5.6)."""

    primary_modality: PrimaryModality = PrimaryModality.TEXT
    text_content: Optional[str] = None
    semantic_description: Optional[str] = None
    ocr_text: Optional[str] = None
    document_summary: Optional[DocumentSummary] = None
    location_description: Optional[str] = None
    emotional_register_hint: Optional[str] = None
    modality_flags: list[str] = field(default_factory=list)
    raw_voice_available: bool = False              # True only during SC-4; False in final packet
    language_detected: Optional[str] = None        # ISO 639-1
    language_switch_detected: bool = False


# ────────────────────────────────────────────────────────────────────────────
# Voice prosody sub-component types (SC-4)
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class ProsodyFeatures:
    """Raw prosodic measurements (architecture doc §6.2)."""

    speech_rate_words_per_min: float = 0.0
    speech_rate_deviation: float = 0.0
    pitch_mean_hz: float = 0.0
    pitch_variance: float = 0.0
    energy_mean_db: float = 0.0
    energy_variance: float = 0.0
    pause_frequency: float = 0.0
    pause_mean_duration_ms: float = 0.0
    voice_tremor_detected: bool = False
    vocal_fry_detected: bool = False
    breathiness_score: float = 0.0                 # 0–1


@dataclass
class ProsodyEmotionEstimate:
    """Derived prosodic emotion estimate (architecture doc §6.2)."""

    valence: float = 0.0       # –1 (negative) … +1 (positive)
    arousal: float = 0.0       # 0 (calm) … 1 (activated)
    confidence: float = 0.0    # 0–1; lower for noisy audio
    dominant_signal: Optional[ProsodyDominantSignal] = None


@dataclass
class UserBehaviorBaseline:
    """In-memory projection of the per-user rolling-history tables (architecture doc §8).

    The Temporal Resolver / Implicit Signal Extractor read these baselines every message;
    the Layer 2 State Updater appends to the underlying ``user_meta.db`` history after each
    turn. ``None`` fields mean "no baseline yet" (new user) and yield neutral signals.
    """

    latency_median_ms: Optional[float] = None          # rolling median, last 50 messages (§4.2)
    message_length_median_chars: Optional[float] = None  # rolling median, last 100 messages (§4.4)
    shortest_recent_gap_seconds: Optional[float] = None  # shortest gap in last 30 days (§3.4)


@dataclass
class VoiceCalibrationProfile:
    """Per-user voice baseline, built after 5+ voice inputs (architecture doc §6.3)."""

    baseline_speech_rate: float = 0.0
    baseline_pitch_mean: float = 0.0
    baseline_pitch_variance: float = 0.0
    baseline_energy_mean: float = 0.0
    samples_used: int = 0
    calibration_confidence: float = 0.0            # 0–1; <0.5 until 10+ samples


# ────────────────────────────────────────────────────────────────────────────
# Service interface payloads (architecture doc §12.2)
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class AttachmentPayload:
    """A single non-text attachment accompanying a message.

    ``data`` holds raw bytes in RAM only — never persisted (§6.4 privacy constraint).
    """

    attachment_type: AttachmentType
    mime_type: Optional[str] = None
    data: Optional[bytes] = None
    filename: Optional[str] = None
    size_bytes: Optional[int] = None
    # Location attachments only:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_name: Optional[str] = None
    # Reaction attachments only:
    reaction_emoji: Optional[str] = None


@dataclass
class ClientMetadata:
    """Behavioral metadata the client app reports alongside every message (§12.2).

    The two ``*_proactive`` fields extend the original spec so SC-2 can resolve
    ``initiation_type`` without reaching into Layer 6 (see architecture doc §4.5 — the
    server cannot derive whether the previous Nova turn was a proactive reach-out).
    """

    session_id: UUID
    nova_last_delivered_at: Optional[datetime] = None
    user_typing_started_at: Optional[datetime] = None
    deletion_occurred: bool = False
    deletion_count: int = 0
    peak_draft_length_chars: int = 0
    final_draft_length_chars: int = 0
    is_burst: bool = False
    burst_count: int = 1
    burst_messages: Optional[list[str]] = None
    last_nova_message_was_proactive: bool = False
    is_reply_to_proactive: bool = False


# ────────────────────────────────────────────────────────────────────────────
# The Layer 1 output contract
# ────────────────────────────────────────────────────────────────────────────
def _unset_fuzzy(_ts: datetime) -> str:  # pragma: no cover - replaced by the assembler
    return "some time ago"


@dataclass
class InputPerceptionPacket:
    """The complete, read-only output of Layer 1 (architecture doc §7.3).

    Every downstream layer consumes a subset of these fields (§9 consumption contract).
    Non-default identity/timing fields come first; all signal fields default so the
    assembler can always emit a populated packet even on partial failure (§11).
    """

    # ── Identity & timing ───────────────────────────────────────────────
    user_id: UUID
    message_id: UUID
    received_at: datetime
    user_local_time: Optional[time] = None
    circadian_band: str = CircadianBand.AFTERNOON.value
    circadian_mood_prior: float = 0.25
    day_of_week: str = ""
    is_weekend: bool = False

    # ── Session gap ─────────────────────────────────────────────────────
    session_gap_seconds: int = 0
    gap_category: str = GapCategory.SAME_SESSION.value
    human_readable_gap_label: str = "just now"
    is_new_session: bool = False

    # ── Temporal anomaly ────────────────────────────────────────────────
    anomaly_detected: bool = False
    context_note: Optional[str] = None

    # ── Relationship temporal context ───────────────────────────────────
    relationship_age_days: int = 0
    total_sessions_with_user: int = 0
    avg_session_frequency_days: float = 0.0
    gap_vs_baseline_ratio: float = 1.0

    # ── Pending threads ─────────────────────────────────────────────────
    due_threads: list[NarrativeThread] = field(default_factory=list)  # max 2, priority sorted
    overdue_thread_count: int = 0

    # ── Fuzzy label helper ──────────────────────────────────────────────
    fuzzy_label_for_timestamp: Callable[[datetime], str] = _unset_fuzzy

    # ── Implicit signals ────────────────────────────────────────────────
    response_latency_ms: Optional[int] = None
    latency_signal: Optional[str] = None
    latency_deviation_from_baseline: Optional[float] = None
    deletion_occurred: bool = False
    deletion_count: int = 0
    final_length_vs_peak_ratio: Optional[float] = None
    message_length_chars: int = 0
    length_ratio_vs_baseline: float = 1.0
    initiation_type: str = InitiationType.USER_INITIATED_COLD.value
    is_message_burst: bool = False
    burst_count: int = 1
    implicit_emotional_intensity_score: float = 0.0

    # ── Modality ────────────────────────────────────────────────────────
    primary_modality: str = PrimaryModality.TEXT.value
    raw_text: Optional[str] = None
    modality_context: ModalityContext = field(default_factory=ModalityContext)

    # ── Prosody (voice only) ────────────────────────────────────────────
    prosody_features: Optional[ProsodyFeatures] = None
    prosody_emotion_estimate: Optional[ProsodyEmotionEstimate] = None
    signal_mismatch: bool = False

    # ── Composite pre-linguistic emotional prior ────────────────────────
    composite_emotional_prior: float = 0.0
    prior_confidence: float = 0.0

    # ── Diagnostic flags (architecture doc §11 fallback behaviors) ──────
    cold_start_profile: bool = False
    timezone_confidence: str = "high"   # "high" | "low"
