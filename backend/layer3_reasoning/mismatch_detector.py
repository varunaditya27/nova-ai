"""SC-4 — Stated-vs-Felt Mismatch Detector (architecture doc §6).

When the text says one thing ("I'm fine") but the totality of pre-linguistic signals says
another, this detector flags the gap and — critically — selects a *posture*, not a
diagnosis. The correct behaviour is "create space without forcing" (§6.3): a single gentle
opening, a relationship-gated direct noticing, or simply holding and watching when the
signal is too weak to act on.
"""

from __future__ import annotations

from typing import Optional

from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    BESLabel,
    EmotionClassification,
    MismatchPosture,
    MismatchResult,
    MismatchType,
)

HEDGING_PHRASES = [
    "kind of", "sort of", "i guess", "maybe", "a bit", "slightly",
    "not really", "i don't know", "whatever", "it's fine", "it's okay",
    "doesn't matter", "never mind", "forget it",
]

DEFLECTION_PHRASES = [
    "i'm fine", "i'm okay", "i'm good", "don't worry about it",
    "it's nothing", "all good", "not a big deal", "i'll be fine",
]

# Display spellings (for surfacing back in the result with natural capitalisation).
_DEFLECTION_DISPLAY = {
    "i'm fine": "I'm fine", "i'm okay": "I'm okay", "i'm good": "I'm good",
    "don't worry about it": "don't worry about it", "it's nothing": "it's nothing",
    "all good": "all good", "not a big deal": "not a big deal", "i'll be fine": "I'll be fine",
}

MISMATCH_MAGNITUDE_THRESHOLD = 0.45
NEGATIVE_BES_LABELS = {
    BESLabel.MILD_NEGATIVE_DRIFT.value,
    BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value,
    BESLabel.DETERIORATING.value,
}


def select_mismatch_posture(
    mismatch_type: Optional[str],
    relationship_depth: float,
    confidence: float,
) -> str:
    """Choose how to hold the mismatch (architecture doc §6.3 posture table)."""
    # Uncertain signal or a new relationship → never force; just watch.
    if confidence < 0.50 or relationship_depth < 0.3:
        return MismatchPosture.HOLD_AND_WATCH.value
    # Direct noticing is reserved for masking with established depth + high confidence.
    if (mismatch_type == MismatchType.MASKING.value
            and relationship_depth >= 0.6 and confidence > 0.80):
        return MismatchPosture.DIRECT_NOTICING.value
    # Default: one gentle opening, then stop.
    return MismatchPosture.GENTLE_ACKNOWLEDGMENT.value


def detect_mismatch(
    primary_emotion: EmotionClassification,
    composite_prior: float,
    implicit_intensity: float,
    prosody_estimate,
    signal_mismatch_flag: bool,
    message: str,
    background_state: BackgroundEmotionalState,
    relationship_depth: float = 0.0,
) -> MismatchResult:
    """Flag and classify a stated-vs-felt gap, then attach a posture (architecture doc §6.2)."""
    lowered = message.lower()

    # Felt valence estimate from pre-linguistic signals: high vulnerability → negative.
    felt_neg = composite_prior
    felt_valence_estimate = -1.0 * felt_neg + (1 - felt_neg) * 0.2
    stated_valence = primary_emotion.valence
    mismatch_magnitude = abs(stated_valence - felt_valence_estimate)

    hedges = [p for p in HEDGING_PHRASES if p in lowered]
    deflections = [_DEFLECTION_DISPLAY.get(p, p) for p in DEFLECTION_PHRASES if p in lowered]

    detected = (
        mismatch_magnitude > MISMATCH_MAGNITUDE_THRESHOLD
        or signal_mismatch_flag
        or (len(deflections) > 0 and background_state.bes_label in NEGATIVE_BES_LABELS)
    )

    if not detected:
        return MismatchResult(
            mismatch_detected=False,
            stated_valence=stated_valence,
            felt_valence_estimate=felt_valence_estimate,
            mismatch_magnitude=mismatch_magnitude,
            hedging_phrases_detected=hedges,
            deflection_phrases_detected=deflections,
        )

    # Classify the type of mismatch.
    if stated_valence > 0.2 and felt_valence_estimate < -0.2:
        mismatch_type = MismatchType.MASKING.value
    elif len(hedges) >= 2 and abs(stated_valence) < 0.3:
        mismatch_type = MismatchType.LINGUISTIC_HEDGING.value
    elif stated_valence > felt_valence_estimate and stated_valence > -0.1:
        mismatch_type = MismatchType.MINIMIZING.value
    else:
        mismatch_type = MismatchType.MINIMIZING.value

    confidence = min(0.95, 0.4 + mismatch_magnitude * 0.4 + len(deflections) * 0.15)
    posture = select_mismatch_posture(mismatch_type, relationship_depth, confidence)

    return MismatchResult(
        mismatch_detected=True,
        mismatch_type=mismatch_type,
        stated_valence=stated_valence,
        felt_valence_estimate=felt_valence_estimate,
        mismatch_magnitude=mismatch_magnitude,
        mismatch_confidence=confidence,
        hedging_phrases_detected=hedges,
        deflection_phrases_detected=deflections,
        mismatch_response_posture=posture,
    )
