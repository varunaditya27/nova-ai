"""SC-6 + the EmotionIntentPacket contract (architecture doc §8, §9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from backend.layer2_memory.schemas import ConversationMode, EmotionVector

from .background_state import BackgroundEmotionalState
from .empathy import EmpathyHypothesis
from .emotion import EmotionClassification
from .intent import IntentClassification, TopicDomain
from .mismatch import MismatchResult


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
