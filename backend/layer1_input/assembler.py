"""Layer 1 · Sub-Component 5 — Input Perception Assembler (architecture doc §7).

Not a processor — a *collector and validator*. It gathers the outputs of SC-1…SC-4, resolves
conflicts between signals (§7.2), computes the composite emotional prior (§7.4), and emits the
single read-only ``InputPerceptionPacket`` every downstream layer consumes.

Pipeline within the assembler (resolves the §7.2 / §7.4 overlap into one deterministic order):
  1. Apply conflict rule 1 — derive the *effective* circadian prior from the raw circadian
     prior and the implicit intensity.
  2. Apply conflict rule 2 — set ``signal_mismatch`` from the prosody estimate.
  3. Feed the effective circadian prior into the §7.4 composite formula.

The conflict-resolution math itself lives in ``conflict_resolution.py``; re-exported here so
``assembler.resolve_effective_circadian`` etc. keep working for existing callers/tests.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Callable, Optional
from uuid import UUID

from .conflict_resolution import (
    compute_composite_prior,
    detect_signal_mismatch,
    resolve_effective_circadian,
)
from .schemas import InputPerceptionPacket, ModalityContext, NarrativeThread, ProsodyEmotionEstimate, ProsodyFeatures
from .config import Layer1Config

__all__ = [
    "assemble",
    "compute_composite_prior",
    "detect_signal_mismatch",
    "resolve_effective_circadian",
]


def assemble(
    *,
    user_id: UUID,
    message_id: UUID,
    received_at: datetime,
    user_local_time: Optional[time],
    circadian_band: str,
    circadian_mood_prior: float,
    day_of_week: str,
    is_weekend: bool,
    session_gap_seconds: int,
    gap_category: str,
    human_readable_gap_label: str,
    is_new_session: bool,
    anomaly_detected: bool,
    context_note: Optional[str],
    relationship_age_days: int,
    total_sessions_with_user: int,
    avg_session_frequency_days: float,
    gap_vs_baseline_ratio: float,
    due_threads: list[NarrativeThread],
    overdue_thread_count: int,
    fuzzy_label_for_timestamp: Callable[[datetime], str],
    response_latency_ms: Optional[int],
    latency_signal: Optional[str],
    latency_deviation_from_baseline: Optional[float],
    deletion_occurred: bool,
    deletion_count: int,
    final_length_vs_peak_ratio: Optional[float],
    message_length_chars: int,
    length_ratio_vs_baseline: float,
    initiation_type: str,
    is_message_burst: bool,
    burst_count: int,
    implicit_emotional_intensity_score: float,
    modality_context: ModalityContext,
    raw_text: Optional[str],
    prosody_features: Optional[ProsodyFeatures],
    prosody_emotion_estimate: Optional[ProsodyEmotionEstimate],
    cold_start_profile: bool = False,
    timezone_confidence: str = "high",
    cfg: Optional[Layer1Config] = None,
) -> InputPerceptionPacket:
    """Validate and compose every sub-component output into the final packet (§7.3)."""

    # Step 1 — conflict rule 1: effective circadian prior.
    effective_circadian = resolve_effective_circadian(
        circadian_mood_prior, implicit_emotional_intensity_score, cfg
    )

    # Step 2 — conflict rule 2: prosody mismatch flag.
    signal_mismatch = detect_signal_mismatch(prosody_emotion_estimate, cfg)

    # Step 3 — composite emotional prior (§7.4).
    composite_prior, prior_confidence = compute_composite_prior(
        effective_circadian,
        implicit_emotional_intensity_score,
        prosody_emotion_estimate,
        anomaly_detected,
        cfg,
    )

    return InputPerceptionPacket(
        user_id=user_id,
        message_id=message_id,
        received_at=received_at,
        user_local_time=user_local_time,
        circadian_band=circadian_band,
        circadian_mood_prior=circadian_mood_prior,
        day_of_week=day_of_week,
        is_weekend=is_weekend,
        session_gap_seconds=session_gap_seconds,
        gap_category=gap_category,
        human_readable_gap_label=human_readable_gap_label,
        is_new_session=is_new_session,
        anomaly_detected=anomaly_detected,
        context_note=context_note,
        relationship_age_days=relationship_age_days,
        total_sessions_with_user=total_sessions_with_user,
        avg_session_frequency_days=avg_session_frequency_days,
        gap_vs_baseline_ratio=gap_vs_baseline_ratio,
        due_threads=due_threads,
        overdue_thread_count=overdue_thread_count,
        fuzzy_label_for_timestamp=fuzzy_label_for_timestamp,
        response_latency_ms=response_latency_ms,
        latency_signal=latency_signal,
        latency_deviation_from_baseline=latency_deviation_from_baseline,
        deletion_occurred=deletion_occurred,
        deletion_count=deletion_count,
        final_length_vs_peak_ratio=final_length_vs_peak_ratio,
        message_length_chars=message_length_chars,
        length_ratio_vs_baseline=length_ratio_vs_baseline,
        initiation_type=initiation_type,
        is_message_burst=is_message_burst,
        burst_count=burst_count,
        implicit_emotional_intensity_score=implicit_emotional_intensity_score,
        primary_modality=modality_context.primary_modality.value,
        raw_text=raw_text,
        modality_context=modality_context,
        prosody_features=prosody_features,
        prosody_emotion_estimate=prosody_emotion_estimate,
        signal_mismatch=signal_mismatch,
        composite_emotional_prior=composite_prior,
        prior_confidence=prior_confidence,
        cold_start_profile=cold_start_profile,
        timezone_confidence=timezone_confidence,
    )
