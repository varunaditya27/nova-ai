"""SC-1 temporal sub-component types (architecture doc §3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from .enums import ImportanceTier, ThreadStatus, ThreadType


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
    longest_historical_gap_days: float = 0.0
    last_session_end: Optional[datetime] = None
    total_sessions: int = 0
    relationship_age_days: int = 0
    per_band_circadian_prior: dict[str, float] = field(default_factory=dict)


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
