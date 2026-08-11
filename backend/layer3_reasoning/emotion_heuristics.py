"""SC-1 deterministic heuristic pre-filter (architecture doc §3.3).

Catches unambiguous signals (crisis, celebration, pure-informational) in <1ms so the
LLM pass can be skipped or crisis flags preserved regardless of what the LLM says.
"""

from __future__ import annotations

from typing import Optional

from backend.layer3_reasoning.schemas import (
    ClassificationMethod,
    CrisisType,
    EmotionClassification,
    EmotionLabel,
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
