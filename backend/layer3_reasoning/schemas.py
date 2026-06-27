"""Schemas for Layer 3 — Emotion, Intent & Reasoning (architecture doc §3–§9).

Layer 3 is the interpretive core. Its six sub-components synthesise every upstream
signal into a single read-only ``EmotionIntentPacket`` consumed by all response-
generation layers.

Reuse over redefinition: ``EmotionVector`` and ``ConversationMode`` are owned by
Layer 2 (the pipeline runs L1→L2→L3, so L3 imports downstream-safe types rather than
duplicating them). This keeps a single source of truth for the emotion vector and the
canonical eight-mode taxonomy.

All enums subclass ``str`` so a field compares equal to its plain-string spelling
(``packet.conversation_mode == "crisis"``) while remaining type-checked. All scored
floats stay inside Layer 3 — only the plain-language ``*_instruction`` strings and the
``advice_gate`` cross the boundary to the LLM (architecture doc §10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

# Canonical types owned upstream (single source of truth).
from backend.layer2_memory.schemas import ConversationMode, EmotionVector

__all__ = [
    "ConversationMode",
    "EmotionVector",
    "EmotionLabel",
    "CrisisType",
    "ClassificationMethod",
    "SecondaryEmotion",
    "EmotionClassification",
    "EMOTION_TAXONOMY",
    "BESLabel",
    "BackgroundEmotionalState",
    "IntentLabel",
    "TopicDomain",
    "IntentClassification",
    "MismatchType",
    "MismatchPosture",
    "MismatchResult",
    "PrimaryNeed",
    "ResponsePosture",
    "DisclosureDepth",
    "EmpathyHypothesis",
    "AdviceGate",
    "ResponsePacing",
    "LLMClassificationOutput",
    "CrisisAlert",
    "EmotionIntentPacket",
]


# ── SC-1 Primary Emotion Classifier (§3) ──────────────────────────────────────
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


# ── SC-2 Background Emotional State Tracker (§4) ───────────────────────────────
class BESLabel(str, Enum):
    """Derived background-state label (architecture doc §4.3)."""

    STABLE_POSITIVE = "stable_positive"
    STABLE_NEUTRAL = "stable_neutral"
    MILD_NEGATIVE_DRIFT = "mild_negative_drift"
    SIGNIFICANT_NEGATIVE_DRIFT = "significant_negative_drift"
    IMPROVING = "improving"
    DETERIORATING = "deteriorating"
    VOLATILE = "volatile"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class BackgroundEmotionalState:
    """The user's emotional drift across time (architecture doc §4.3)."""

    valence_14day_mean: float = 0.0
    valence_trend: float = 0.0
    arousal_14day_mean: float = 0.0
    stressor_load: float = 0.0
    bes_label: str = BESLabel.INSUFFICIENT_DATA.value
    regulation_adjustment_applied: bool = False
    regulation_style: Optional[str] = None
    confidence: float = 0.0
    data_points_used: int = 0
    trend_note: Optional[str] = None


# ── SC-3 Intent Classifier (§5) ───────────────────────────────────────────────
class IntentLabel(str, Enum):
    """What the user is trying to accomplish (architecture doc §5.2)."""

    # Relational / emotional.
    VENTING = "venting"
    SEEKING_VALIDATION = "seeking_validation"
    SEEKING_COMFORT = "seeking_comfort"
    SHARING_GOOD_NEWS = "sharing_good_news"
    CASUAL_CHAT = "casual_chat"
    CHECK_IN = "check_in"
    # Cognitive / task.
    SEEKING_ADVICE = "seeking_advice"
    SEEKING_INFORMATION = "seeking_information"
    THINKING_ALOUD = "thinking_aloud"
    PROBLEM_SOLVING = "problem_solving"
    GOAL_SETTING = "goal_setting"
    DECISION_SUPPORT = "decision_support"
    # Meta / relational.
    PROVIDING_UPDATE = "providing_update"
    EXPRESSING_GRATITUDE = "expressing_gratitude"
    EXPRESSING_COMPLAINT = "expressing_complaint"
    TESTING_NOVA = "testing_nova"
    REQUESTING_REFLECTION = "requesting_reflection"


class TopicDomain(str, Enum):
    """Subject matter of the conversation (architecture doc §5.5)."""

    ACADEMICS = "academics"
    CAREER = "career"
    RELATIONSHIPS = "relationships"
    HEALTH = "health"
    EXISTENTIAL = "existential"
    SOCIAL = "social"
    OTHER = "other"


@dataclass
class IntentClassification:
    """What the user needs from Nova right now (architecture doc §5)."""

    primary_intent: str = IntentLabel.CASUAL_CHAT.value
    secondary_intent: Optional[str] = None
    intent_confidence: float = 0.0
    needs_advice: bool = False
    needs_validation: bool = False
    prefers_no_advice: bool = False
    topic_domain: str = TopicDomain.OTHER.value
    classification_method: str = ClassificationMethod.HEURISTIC_ONLY.value


# ── SC-4 Stated-vs-Felt Mismatch Detector (§6) ────────────────────────────────
class MismatchType(str, Enum):
    """How the stated emotion diverges from the felt estimate (architecture doc §6.2)."""

    MINIMIZING = "minimizing"
    MASKING = "masking"
    OVERCLAIMING = "overclaiming"
    LINGUISTIC_HEDGING = "linguistic_hedging"


class MismatchPosture(str, Enum):
    """How Nova should hold a detected mismatch (architecture doc §6.3)."""

    GENTLE_ACKNOWLEDGMENT = "gentle_acknowledgment"  # Posture 1 (default)
    DIRECT_NOTICING = "direct_noticing"              # Posture 2 (needs depth + confidence)
    HOLD_AND_WATCH = "hold_and_watch"                # Posture 3 (uncertain / new relationship)


@dataclass
class MismatchResult:
    """Gap between stated content and felt state (architecture doc §6.2)."""

    mismatch_detected: bool = False
    mismatch_type: Optional[str] = None
    stated_valence: float = 0.0
    felt_valence_estimate: float = 0.0
    mismatch_magnitude: float = 0.0
    mismatch_confidence: float = 0.0
    hedging_phrases_detected: list[str] = field(default_factory=list)
    deflection_phrases_detected: list[str] = field(default_factory=list)
    mismatch_response_posture: Optional[str] = None


# ── SC-5 Empathy Hypothesis Generator (§7) ────────────────────────────────────
class PrimaryNeed(str, Enum):
    """What the user most needs from Nova (architecture doc §7.2)."""

    TO_BE_HEARD = "to_be_heard"
    TO_BE_VALIDATED = "to_be_validated"
    TO_CELEBRATE = "to_celebrate"
    TO_PROBLEM_SOLVE = "to_problem_solve"
    TO_THINK_ALOUD = "to_think_aloud"
    TO_DECIDE = "to_decide"
    SPACE_TO_SIT_WITH_IT = "space_to_sit_with_it"
    INFORMATION = "information"
    DISTRACTION = "distraction"
    CRISIS_SUPPORT = "crisis_support"


class ResponsePosture(str, Enum):
    """The governing response stance (architecture doc §7.2)."""

    VALIDATE_THEN_HOLD = "validate_then_hold"
    VALIDATE_THEN_SOLVE = "validate_then_solve"
    CELEBRATE = "celebrate"
    CO_THINK = "co_think"
    INFORM_WITH_WARMTH = "inform_with_warmth"
    GENTLE_REDIRECT = "gentle_redirect"
    LISTEN_ONLY = "listen_only"
    CRISIS_PROTOCOL = "crisis_protocol"


class DisclosureDepth(str, Enum):
    """How much relational depth the response may assume (architecture doc §7.2)."""

    SURFACE = "surface"
    MODERATE = "moderate"
    DEEP = "deep"


@dataclass
class EmpathyHypothesis:
    """Auditable internal reasoning bridging classification and generation (§7.2)."""

    primary_feeling: str = ""
    feeling_basis: str = ""
    secondary_feeling: Optional[str] = None
    primary_need: str = PrimaryNeed.INFORMATION.value
    secondary_need: Optional[str] = None
    response_posture: str = ResponsePosture.INFORM_WITH_WARMTH.value
    advice_withheld: bool = False
    advice_withheld_reason: Optional[str] = None
    apply_mismatch_posture: bool = False
    mismatch_posture: Optional[str] = None
    disclosure_depth_allowed: str = DisclosureDepth.SURFACE.value
    is_crisis: bool = False
    skip_emotional_refinement: bool = False
    generated_at: datetime = field(default_factory=datetime.utcnow)
    basis_summary: str = ""


# ── SC-6 + EmotionIntentPacket (§8, §9) ───────────────────────────────────────
class AdviceGate(str, Enum):
    """Whether the Semantic Planner may offer advice (architecture doc §9)."""

    OPEN = "open"      # give freely
    GATED = "gated"    # only if asked
    CLOSED = "closed"  # no advice


class ResponsePacing(str, Enum):
    """Layer 9 pacing hint (architecture doc §9)."""

    IMMEDIATE = "immediate"
    NORMAL = "normal"
    SLOW = "slow"
    CONTEMPLATIVE = "contemplative"


@dataclass
class CrisisAlert:
    """Fast parallel alert emitted to Layer 8 + Layer 11 (architecture doc §3.6)."""

    alert_id: UUID = field(default_factory=uuid4)
    crisis_confidence: float = 0.0
    crisis_type: Optional[str] = None
    message_excerpt: str = ""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "layer3_heuristic"  # "layer3_heuristic" | "layer3_llm"


@dataclass
class EmotionIntentPacket:
    """The read-only contract Layer 3 hands to all downstream layers (architecture doc §9).

    Computed once per message, never modified after emission. Numeric scores are
    consumed only by orchestration logic; the LLM sees only ``response_instruction``,
    ``emotional_posture_instruction``, ``validation_instruction`` and ``advice_gate``.
    """

    # Primary emotion.
    primary_emotion: EmotionClassification = field(default_factory=EmotionClassification)

    # Background emotional state.
    background_state: BackgroundEmotionalState = field(default_factory=BackgroundEmotionalState)

    # Intent.
    intent: IntentClassification = field(default_factory=IntentClassification)
    topic_domain: str = TopicDomain.OTHER.value
    prefers_no_advice: bool = False
    needs_validation_first: bool = False

    # Mismatch.
    mismatch: MismatchResult = field(default_factory=MismatchResult)
    mismatch_response_posture: Optional[str] = None

    # Empathy hypothesis.
    empathy_hypothesis: EmpathyHypothesis = field(default_factory=EmpathyHypothesis)

    # Conversation mode (single governing label).
    conversation_mode: str = ConversationMode.CASUAL.value

    # Safety flags.
    crisis_active: bool = False
    crisis_type: Optional[str] = None
    crisis_confidence: float = 0.0

    # Response-generation instructions (plain language; no raw scores).
    response_instruction: str = "Respond naturally and warmly."
    emotional_posture_instruction: str = "Warm and attentive."
    validation_instruction: Optional[str] = None
    advice_gate: str = AdviceGate.OPEN.value

    # Layer 9 pacing signal.
    suggested_response_pacing: str = ResponsePacing.NORMAL.value
    suggested_thinking_pause_ms: int = 0

    # Audit.
    classification_latency_ms: int = 0
    llm_call_made: bool = False
    classification_confidence_overall: float = 0.0

    @property
    def emotion_vector(self) -> EmotionVector:
        """Convenience: the primary emotion's (valence, arousal) (architecture doc §9)."""
        return self.primary_emotion.emotion_vector
