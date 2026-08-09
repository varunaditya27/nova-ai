"""Layer 1 · Sub-Component 2 — Implicit Signal Extractor (architecture doc §4).

Reads the *behavioral fingerprint* of a message — how it was sent, not what it says:
latency, edit/deletion behavior, length deviation, initiation type, and burst structure.
These are aggregated into a single ``implicit_emotional_intensity_score`` (§4.7) that gives
Layer 3 a pre-linguistic estimate of emotional load before any content analysis.

Arithmetic only — no model, deterministic, microsecond-scale (§10).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .config import Layer1Config
from .schemas import InitiationType, LatencySignal

_DEFAULT = Layer1Config()


def compute_latency(
    nova_last_delivered_at: Optional[datetime],
    user_typing_started_at: Optional[datetime],
    received_at: datetime,
) -> Optional[int]:
    """Milliseconds between Nova's last message and the user beginning this one (§4.2).

    Uses the typing-start timestamp when available, else the send time. Returns ``None``
    when there is no prior Nova message this session (§11 fallback).
    """
    if nova_last_delivered_at is None:
        return None
    reference = user_typing_started_at or received_at
    delta_ms = (reference - nova_last_delivered_at).total_seconds() * 1000
    return int(max(0.0, delta_ms))


def classify_latency(
    latency_ms: Optional[int], cfg: Optional[Layer1Config] = None
) -> Optional[LatencySignal]:
    """Map a response latency to its interpretation label (§4.2)."""
    if latency_ms is None:
        return None
    c = cfg or _DEFAULT
    for name, upper_bound in sorted(c.latency_thresholds_ms.items(), key=lambda kv: kv[1]):
        if latency_ms < upper_bound:
            return LatencySignal(name)
    return LatencySignal.BREAK


def latency_deviation(
    latency_ms: Optional[int], baseline_ms: Optional[float]
) -> Optional[float]:
    """Latency as a ratio of the user's rolling median (§4.2). ``None`` if either absent."""
    if latency_ms is None or not baseline_ms:
        return None
    return latency_ms / baseline_ms


def deletion_ratio(peak_draft_chars: int, final_draft_chars: int) -> Optional[float]:
    """How much shorter the sent message is than the longest draft (§4.3).

    0.2 means the user wrote 5× what they sent. ``None`` when no draft activity occurred.
    """
    if peak_draft_chars <= 0:
        return None
    return final_draft_chars / peak_draft_chars


def length_ratio(current_chars: int, baseline_chars: Optional[float]) -> float:
    """Current message length over the user's rolling-median baseline (§4.4).

    Defaults to 1.0 (neutral) when no baseline exists yet (new user).
    """
    if not baseline_chars or baseline_chars <= 0:
        return 1.0
    return current_chars / baseline_chars


def resolve_initiation_type(
    is_continuation: bool,
    is_reply_to_proactive: bool,
    last_was_proactive: bool,
) -> InitiationType:
    """Classify how this conversation turn began (§4.5).

    ``is_continuation`` is SC-1's single "ongoing session" decision (``not is_new_session``);
    deriving it once avoids a second, divergent gap-threshold check here.
    """
    if is_continuation:
        return InitiationType.CONTINUATION
    if is_reply_to_proactive:
        return InitiationType.RESPONSE_TO_CHECKIN
    if last_was_proactive:
        return InitiationType.USER_INITIATED_HOT
    return InitiationType.USER_INITIATED_COLD


def is_message_burst(is_burst: bool, burst_count: int) -> bool:
    """True when the user sent multiple messages before Nova responded (§4.6)."""
    return bool(is_burst) and burst_count > 1


def compute_implicit_emotional_intensity(
    latency_signal: Optional[str],
    deletion_occurred: bool,
    deletion_count: int,
    length_ratio: float,
    initiation_type: str,
    cfg: Optional[Layer1Config] = None,
) -> float:
    """Aggregate the five implicit signals into a 0–1 pre-linguistic intensity score.

    Implements the architecture doc §4.7 formula verbatim. This is a weighted pre-signal,
    not a diagnosis — it shifts Layer 3's emotional prior before content analysis.
    """
    c = cfg or _DEFAULT
    score = 0.0

    # Latency contribution.
    score += c.intensity_latency_scale * c.latency_intensity_weights.get(latency_signal or "", 0.0)

    # Deletion contribution.
    if deletion_occurred:
        score += c.intensity_deletion_scale * min(deletion_count / 5.0, 1.0)

    # Length deviation contribution.
    if length_ratio > 4.0:
        score += c.intensity_length_long_scale * min((length_ratio - 4.0) / 4.0, 1.0)
    elif length_ratio < 0.2:
        score += c.intensity_length_withdrawal  # withdrawal signal

    # Initiation contribution.
    if initiation_type == "user_initiated_cold":
        score += c.intensity_initiation_cold

    return min(score, 1.0)
