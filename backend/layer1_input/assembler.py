"""Layer 1 · Sub-Component 5 — Input Perception Assembler (architecture doc §7).

Not a processor — a *collector and validator*. It gathers the outputs of SC-1…SC-4, resolves
conflicts between signals (§7.2), computes the composite emotional prior (§7.4), and emits the
single read-only ``InputPerceptionPacket`` every downstream layer consumes.

Pipeline within the assembler (resolves the §7.2 / §7.4 overlap into one deterministic order):
  1. Apply conflict rule 1 — derive the *effective* circadian prior from the raw circadian
     prior and the implicit intensity.
  2. Apply conflict rule 2 — set ``signal_mismatch`` from the prosody estimate.
  3. Feed the effective circadian prior into the §7.4 composite formula.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Callable, Optional
from uuid import UUID

from .config import Layer1Config
from .schemas import (
    InputPerceptionPacket,
    ModalityContext,
    NarrativeThread,
    ProsodyDominantSignal,
    ProsodyEmotionEstimate,
    ProsodyFeatures,
)

# What each function below falls back to when no ``cfg`` is supplied (every existing unit test).
_DEFAULT = Layer1Config()


def resolve_effective_circadian(
    circadian_mood_prior: float, implicit_intensity: float, cfg: Optional[Layer1Config] = None,
) -> float:
    """Conflict rule 1 (§7.2): high implicit intensity overrides a low-vulnerability band.

    When the circadian prior says the user should be calm (morning/afternoon) but behavioral
    signals say otherwise, the implicit signal wins: ``max(circadian, implicit × 0.8)``.
    """
    c = cfg or _DEFAULT
    if (
        circadian_mood_prior < c.low_vulnerability_prior
        and implicit_intensity >= c.high_implicit_intensity
    ):
        return max(circadian_mood_prior, implicit_intensity * 0.8)
    return circadian_mood_prior


def detect_signal_mismatch(
    prosody_estimate: Optional[ProsodyEmotionEstimate], cfg: Optional[Layer1Config] = None,
) -> bool:
    """Conflict rule 2 (§7.2): prosody signals distress.

    Layer 1 cannot judge text sentiment (that is Layer 3's job), so it raises the flag whenever
    the prosodic channel reads distressed. Layer 3 then applies the full "stated vs. felt" logic
    against the message content.
    """
    if prosody_estimate is None:
        return False
    if prosody_estimate.valence <= (cfg or _DEFAULT).distress_valence_threshold:
        return True
    return prosody_estimate.dominant_signal in (
        ProsodyDominantSignal.ANXIOUS,
        ProsodyDominantSignal.DISTRESSED,
    )


def compute_composite_prior(
    circadian_mood_prior: float,
    implicit_intensity: float,
    prosody_estimate: Optional[ProsodyEmotionEstimate],
    anomaly_detected: bool,
    cfg: Optional[Layer1Config] = None,
) -> tuple[float, float]:
    """Synthesize all pre-linguistic signals into one Bayesian prior for Layer 3 (§7.4).

    Returns ``(prior, confidence)``. Implements the architecture doc §7.4 formula verbatim.
    Confidence rises with the number of contributing signals (1.0 once prosody participates).
    """
    c = cfg or _DEFAULT
    signals: list[float] = []
    weights: list[float] = []

    # Circadian prior — lowest weight (population-level baseline).
    signals.append(circadian_mood_prior)
    weights.append(c.composite_weights["circadian"])

    # Implicit signals — moderate weight (behavioral, user-specific).
    signals.append(implicit_intensity)
    weights.append(c.composite_weights["implicit"])

    # Prosody — highest weight when a confident estimate is present (direct emotional channel).
    if prosody_estimate and prosody_estimate.confidence > c.prosody_min_confidence:
        prosody_neg = max(0.0, -prosody_estimate.valence)  # negative valence → vulnerability
        signals.append(prosody_neg)
        weights.append(c.composite_weights["prosody"])

    # Anomaly bonus — atypical timing nudges every signal up slightly.
    if anomaly_detected:
        signals = [s + c.anomaly_signal_bonus for s in signals]

    total_weight = sum(weights)
    prior = sum(s * w for s, w in zip(signals, weights)) / total_weight
    confidence = min(len(signals) / 3.0, 1.0)

    return min(prior, 1.0), confidence


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
