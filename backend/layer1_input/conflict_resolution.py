"""Layer 1 assembler conflict-resolution + composite-prior math (architecture doc §7.2, §7.4).

Split out of ``assembler.py`` — these are pure functions with no packet-assembly concern.
"""

from __future__ import annotations

from typing import Optional

from .config import Layer1Config
from .schemas import ProsodyDominantSignal, ProsodyEmotionEstimate

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
