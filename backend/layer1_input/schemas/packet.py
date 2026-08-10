"""The Layer 1 output contract (architecture doc §7.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Callable, Optional
from uuid import UUID

from .enums import CircadianBand, GapCategory, InitiationType, PrimaryModality
from .modality import ModalityContext, ProsodyEmotionEstimate, ProsodyFeatures
from .temporal import NarrativeThread


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
