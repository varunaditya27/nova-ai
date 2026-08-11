"""SC-1 Primary Emotion Classifier types (architecture doc §3) + the shared LLM output."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from backend.layer2_memory.schemas import EmotionVector


class EmotionLabel(str, Enum):
    """Discrete emotion taxonomy (architecture doc §3.2, 16 labels)."""

    JOY = "joy"
    CONTENTMENT = "contentment"
    PRIDE = "pride"
    NEUTRAL = "neutral"
    CURIOSITY = "curiosity"
    FRUSTRATION = "frustration"
    ANXIETY = "anxiety"
    SADNESS = "sadness"
    ANGER = "anger"
    SHAME = "shame"
    LONELINESS = "loneliness"
    OVERWHELM = "overwhelm"
    DESPAIR = "despair"
    NUMBNESS = "numbness"
    AMBIVALENCE = "ambivalence"
    RELIEF = "relief"


# Valence/arousal centroid per label (mid-points of the §3.2 ranges). Used by
# ``remap_label`` to keep the discrete label consistent with adjusted v/a after prior
# integration.
EMOTION_TAXONOMY: dict[str, tuple[float, float]] = {
    EmotionLabel.JOY.value: (0.80, 0.65),
    EmotionLabel.CONTENTMENT.value: (0.50, 0.20),
    EmotionLabel.PRIDE.value: (0.60, 0.50),
    EmotionLabel.NEUTRAL.value: (0.00, 0.15),
    EmotionLabel.CURIOSITY.value: (0.30, 0.50),
    EmotionLabel.FRUSTRATION.value: (-0.50, 0.60),
    EmotionLabel.ANXIETY.value: (-0.55, 0.75),
    EmotionLabel.SADNESS.value: (-0.75, 0.20),
    EmotionLabel.ANGER.value: (-0.70, 0.80),
    EmotionLabel.SHAME.value: (-0.75, 0.35),
    EmotionLabel.LONELINESS.value: (-0.60, 0.25),
    EmotionLabel.OVERWHELM.value: (-0.60, 0.75),
    EmotionLabel.DESPAIR.value: (-0.85, 0.10),
    EmotionLabel.NUMBNESS.value: (-0.25, 0.05),
    EmotionLabel.AMBIVALENCE.value: (0.00, 0.40),
    EmotionLabel.RELIEF.value: (0.50, 0.25),
}


class CrisisType(str, Enum):
    """Crisis sub-classification (architecture doc §3.5)."""

    SELF_HARM_IDEATION = "self_harm_ideation"
    SUICIDAL_IDEATION = "suicidal_ideation"
    HARM_TO_OTHERS = "harm_to_others"
    ACUTE_DISTRESS_NON_CRISIS = "acute_distress_non_crisis"


class ClassificationMethod(str, Enum):
    """Provenance of the emotion classification (architecture doc §3.5, §12)."""

    HEURISTIC_ONLY = "heuristic_only"
    LLM_ONLY = "llm_only"
    LLM_PLUS_PRIOR = "llm_plus_prior"


@dataclass
class SecondaryEmotion:
    """A co-active emotion with its own confidence (architecture doc §3.5)."""

    label: str
    confidence: float


@dataclass
class EmotionClassification:
    """Message-level emotional assessment (architecture doc §3.5)."""

    primary_label: str = EmotionLabel.NEUTRAL.value
    secondary_labels: list[SecondaryEmotion] = field(default_factory=list)
    valence: float = 0.0
    arousal: float = 0.0
    confidence: float = 0.0

    # Crisis signalling (safety-critical path).
    crisis_flag: bool = False
    crisis_confidence: float = 0.0
    crisis_type: Optional[str] = None

    # Provenance.
    classification_method: str = ClassificationMethod.HEURISTIC_ONLY.value
    prior_was_applied: bool = False
    reasoning_trace: Optional[str] = None

    @property
    def emotion_vector(self) -> EmotionVector:
        """(valence, arousal) as the canonical named struct."""
        return EmotionVector(valence=self.valence, arousal=self.arousal)

    @property
    def intensity(self) -> float:
        """sqrt(valence² + arousal²) / sqrt(2); normalised 0–1 (architecture doc §3.5)."""
        return min(1.0, (self.valence ** 2 + self.arousal ** 2) ** 0.5 / (2 ** 0.5))


@dataclass
class LLMClassificationOutput:
    """Raw shared-call output before prior integration (architecture doc §14.2).

    Holds both the emotion and intent halves of the single shared LLM call so the
    orchestrator can split them across SC-1 and SC-3 without two inferences.
    """

    # Emotion half.
    primary_label: str = EmotionLabel.NEUTRAL.value
    secondary_labels: list[SecondaryEmotion] = field(default_factory=list)
    valence: float = 0.0
    arousal: float = 0.0
    confidence: float = 0.5
    crisis_flag: bool = False
    crisis_confidence: float = 0.0
    reasoning_trace: Optional[str] = None
    # Intent half.
    primary_intent: str = "casual_chat"
    secondary_intent: Optional[str] = None
    intent_confidence: float = 0.5
    needs_advice: bool = False
    needs_validation: bool = False
    prefers_no_advice: bool = False
    topic_domain: str = "other"
