"""SC-1 — Primary Emotion Classifier (architecture doc §3).

Two-pass hybrid: a deterministic heuristic pre-filter catches unambiguous signals
(crisis, celebration, pure-informational) in <1ms; ambiguous messages fall through to a
fast small-model LLM pass whose raw output is then reconciled against the Layer 1
pre-linguistic prior and (for voice) the prosody estimate via a light Bayesian update.

The LLM is injected (``llm_fn``) so the classifier runs and tests fully offline; the real
Phi-3 Mini / Gemma 2B call drops in unchanged. Crisis detection in the heuristic is never
discarded: even when the LLM disagrees, a heuristic crisis keyword keeps the crisis flag
set (architecture doc §3.6, §12 hard rule).
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer3_reasoning.schemas import (
    EMOTION_TAXONOMY,
    ClassificationMethod,
    CrisisType,
    EmotionClassification,
    EmotionLabel,
    LLMClassificationOutput,
)

# Crisis phrases split by type so the heuristic can populate ``crisis_type`` directly
# (architecture doc §3.3 lists the phrases; §3.5 defines the types).
SUICIDAL_KEYWORDS = [
    "want to die", "end it", "can't go on", "no point anymore",
    "kill myself", "disappear", "giving up on life",
]
SELF_HARM_KEYWORDS = ["hurt myself", "harm myself", "cut myself"]
HARM_TO_OTHERS_KEYWORDS = ["hurt them", "kill him", "kill her", "make them pay"]

CELEBRATION_PATTERNS = [
    "i got the job", "i got in", "i passed", "we won", "got promoted",
]

# Confidence ceiling when the LLM is unavailable and we fall back to heuristics (§12).
HEURISTIC_DEGRADED_CONFIDENCE_CAP = 0.65

LLMFn = Callable[[str], LLMClassificationOutput]


def _clamp_valence(v: float) -> float:
    return max(-1.0, min(1.0, v))


def _clamp_arousal(a: float) -> float:
    return max(0.0, min(1.0, a))


def heuristic_prefilter(
    message: str,
    implicit_intensity: float,
    circadian_band: str,
    prosody_estimate=None,
) -> Optional[EmotionClassification]:
    """Return a classification directly for unambiguous signals, else ``None`` (§3.3).

    A returned ``neutral`` label means the message is purely informational and the LLM
    pass can be skipped; a returned crisis/celebration label still wants LLM confirmation
    but carries a usable result on its own.
    """
    lowered = message.lower()

    # Crisis keywords — highest priority, always flagged.
    for kw in SUICIDAL_KEYWORDS:
        if kw in lowered:
            return EmotionClassification(
                primary_label=EmotionLabel.DESPAIR.value,
                valence=-0.95, arousal=0.10, confidence=0.97,
                crisis_flag=True, crisis_confidence=0.97,
                crisis_type=CrisisType.SUICIDAL_IDEATION.value,
                classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
            )
    for kw in SELF_HARM_KEYWORDS:
        if kw in lowered:
            return EmotionClassification(
                primary_label=EmotionLabel.DESPAIR.value,
                valence=-0.90, arousal=0.20, confidence=0.95,
                crisis_flag=True, crisis_confidence=0.95,
                crisis_type=CrisisType.SELF_HARM_IDEATION.value,
                classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
            )
    for kw in HARM_TO_OTHERS_KEYWORDS:
        if kw in lowered:
            return EmotionClassification(
                primary_label=EmotionLabel.ANGER.value,
                valence=-0.80, arousal=0.85, confidence=0.90,
                crisis_flag=True, crisis_confidence=0.90,
                crisis_type=CrisisType.HARM_TO_OTHERS.value,
                classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
            )

    # Celebration — only when the implicit signal isn't screaming distress.
    for pat in CELEBRATION_PATTERNS:
        if pat in lowered and implicit_intensity < 0.3:
            return EmotionClassification(
                primary_label=EmotionLabel.JOY.value,
                valence=0.85, arousal=0.70, confidence=0.88,
                classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
            )

    # Neutral informational — no emotional content at all; LLM not needed.
    if (
        implicit_intensity < 0.1
        and len(message.split()) < 15
        and not any(c in message for c in ("?", "!"))
        and circadian_band not in ("late_night", "early_morning")
    ):
        return EmotionClassification(
            primary_label=EmotionLabel.NEUTRAL.value,
            valence=0.0, arousal=0.05, confidence=0.75,
            classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
        )

    return None  # Ambiguous; proceed to LLM pass.


def remap_label(valence: float, arousal: float, fallback: str) -> str:
    """Pick the taxonomy label whose centroid is nearest the adjusted (v, a) (§3.4).

    After prior/prosody integration the numeric vector may no longer match the LLM's
    discrete label, so we re-snap to the closest centroid to keep them consistent.
    """
    best_label = fallback
    best_dist = float("inf")
    for label, (cv, ca) in EMOTION_TAXONOMY.items():
        dist = (valence - cv) ** 2 + (arousal - ca) ** 2
        if dist < best_dist:
            best_dist = dist
            best_label = label
    return best_label


def integrate_prior(
    llm_output: LLMClassificationOutput,
    composite_prior: float,
    prior_confidence: float,
    prosody_estimate=None,
) -> EmotionClassification:
    """Reconcile the LLM result with the pre-linguistic prior + prosody (§3.4)."""
    adjusted_valence = llm_output.valence
    adjusted_arousal = llm_output.arousal
    prior_applied = False

    # Prior influence: scaled by prior_confidence. A confident, vulnerable prior pulls a
    # too-rosy LLM read toward the negative.
    if prior_confidence > 0.5 and composite_prior > 0.6:
        prior_shift = (composite_prior - 0.5) * prior_confidence * 0.25
        adjusted_valence -= prior_shift
        adjusted_arousal += prior_shift * 0.5
        prior_applied = True

    # Prosody override: high-confidence prosody that sharply conflicts → 60/40 blend.
    if (
        prosody_estimate is not None
        and getattr(prosody_estimate, "confidence", 0.0) > 0.7
        and abs(prosody_estimate.valence - llm_output.valence) > 0.4
    ):
        adjusted_valence = 0.6 * adjusted_valence + 0.4 * prosody_estimate.valence
        adjusted_arousal = 0.6 * adjusted_arousal + 0.4 * prosody_estimate.arousal

    adjusted_valence = _clamp_valence(adjusted_valence)
    adjusted_arousal = _clamp_arousal(adjusted_arousal)

    method = (
        ClassificationMethod.LLM_PLUS_PRIOR.value
        if prior_applied
        else ClassificationMethod.LLM_ONLY.value
    )

    return EmotionClassification(
        primary_label=remap_label(adjusted_valence, adjusted_arousal, llm_output.primary_label),
        secondary_labels=list(llm_output.secondary_labels),
        valence=adjusted_valence,
        arousal=adjusted_arousal,
        confidence=min(1.0, llm_output.confidence * (0.8 + 0.2 * prior_confidence)),
        crisis_flag=llm_output.crisis_flag,
        crisis_confidence=llm_output.crisis_confidence,
        classification_method=method,
        prior_was_applied=prior_applied,
        reasoning_trace=llm_output.reasoning_trace,
    )


def classify_emotion(
    message: str,
    *,
    implicit_intensity: float = 0.0,
    circadian_band: str = "afternoon",
    composite_prior: float = 0.0,
    prior_confidence: float = 0.0,
    prosody_estimate=None,
    llm_fn: Optional[LLMFn] = None,
) -> EmotionClassification:
    """Full SC-1 path: heuristic → (skip | LLM + prior), with crisis preserved (§3.3, §12)."""
    heuristic = heuristic_prefilter(message, implicit_intensity, circadian_band, prosody_estimate)

    # Pure informational message → skip the LLM entirely.
    if heuristic is not None and heuristic.primary_label == EmotionLabel.NEUTRAL.value:
        return heuristic

    # No LLM available → degrade gracefully (architecture doc §12).
    if llm_fn is None:
        if heuristic is not None:
            heuristic.confidence = min(heuristic.confidence, HEURISTIC_DEGRADED_CONFIDENCE_CAP)
            return heuristic
        return EmotionClassification(
            primary_label=EmotionLabel.NEUTRAL.value,
            valence=0.0, arousal=0.05,
            confidence=HEURISTIC_DEGRADED_CONFIDENCE_CAP,
            classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
        )

    llm_output = llm_fn(message)
    clf = integrate_prior(llm_output, composite_prior, prior_confidence, prosody_estimate)

    # A heuristic crisis is never overridden by a calmer LLM read (§3.6 hard rule).
    if heuristic is not None and heuristic.crisis_flag:
        clf.crisis_flag = True
        clf.crisis_confidence = max(clf.crisis_confidence, heuristic.crisis_confidence)
        clf.crisis_type = clf.crisis_type or heuristic.crisis_type
        if clf.primary_label not in (EmotionLabel.DESPAIR.value, EmotionLabel.ANGER.value):
            clf.primary_label = heuristic.primary_label

    return clf
