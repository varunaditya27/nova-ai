"""Schemas for Layer 4 — Persona, Personality & Response Generation.

Layer 4 answers *who is responding and how*. It converges every upstream signal
(temporal context, recalled memory, emotion/intent classification, empathy
hypothesis, conversation mode) into an actual response: language, tone, content,
structure, phrasing, and personality expression.

The layer is three sequential sub-systems (architecture doc §1–2):

    Persona Engine (SC-1..SC-4)  →  PersonaPacket
        SC-1 Persona State Resolver      (persona_resolver.py)
        SC-2 Relationship State Manager  (relationship_manager.py)
        SC-3 Tone & Style Calibrator     (tone_calibrator.py)
        SC-4 Persona Drift Detector      (drift_detector.py)
    Semantic Planner / Agent 4a (SC-5)   →  SemanticDraft   (semantic_planner.py)
    Emotion Refiner / Agent 4b  (SC-6)   →  FinalResponsePacket (emotion_refiner.py)

The orchestrator (packet_builder.py) runs SC-1..SC-6 and emits the
``FinalResponsePacket`` consumed by Layers 2, 5, 6, 7, 9, 12.

Type reuse (single source of truth): this module imports the upstream packets and
the shared enums rather than redefining them. ``ConversationMode`` lives in
Layer 2; the emotion/intent classification types live in Layer 3.

Reconciliation note (architecture doc §3.4, §5.3): the doc references
``PsychologicalModel`` fields that do not exist in the implemented Layer 2 schema
(``humor_receptivity``, ``preferred_interaction_style``, ``known_sensitivities``).
The implemented resolver derives those signals from the fields that *do* exist —
``CommunicationModel.uses_humor`` / ``humor_style`` / ``prefers_direct_answers`` /
``vocabulary_complexity`` and ``PsychologicalModel.preferred_support_style`` /
``known_triggers`` — keeping the layer runnable against the real UWM. See §15
in the architecture doc for the full as-built mapping.

Pure stdlib (dataclasses + str-Enum) so the entire layer runs and tests offline.
Split by sub-component into submodules; this ``__init__`` re-exports everything so
``from backend.layer4_persona.schemas import X`` keeps working unchanged.
"""

from __future__ import annotations

# ── Upstream types (single source of truth) ──────────────────────────────────
from backend.layer2_memory.schemas import (  # noqa: F401  (re-exported)
    ConversationMode,
    ConversationTurn,
    ScoredMemory,
    UWMContextSnapshot,
)
from backend.layer3_reasoning.schemas import (  # noqa: F401  (re-exported)
    AdviceGate,
    BackgroundEmotionalState,
    EmotionIntentPacket,
)

from .drift import DriftDetectionResult
from .enums import (
    ContractionPolicy,
    DriftType,
    HumorMode,
    HumorType,
    MemoryReferencePolicy,
    ParagraphDensity,
    QuestionType,
    RecommendedAction,
    Register,
    RelationshipStage,
    RiskLevel,
    SelfDisclosureDepth,
    SentenceLength,
    TargetResponseLength,
    VocabularyTier,
)
from .packet import (
    AdviceGateValidationResult,
    FactualValidationResult,
    FinalResponsePacket,
    PersonaPacket,
    SemanticDraft,
)
from .persona_state import DynamicPersonaProperty, PersonaState
from .relationship import RelationshipState, SessionSummary
from .voice import VoiceParameters

__all__ = [
    "AdviceGate",
    "AdviceGateValidationResult",
    "BackgroundEmotionalState",
    "ContractionPolicy",
    "ConversationMode",
    "ConversationTurn",
    "DriftDetectionResult",
    "DriftType",
    "DynamicPersonaProperty",
    "EmotionIntentPacket",
    "FactualValidationResult",
    "FinalResponsePacket",
    "HumorMode",
    "HumorType",
    "MemoryReferencePolicy",
    "ParagraphDensity",
    "PersonaPacket",
    "PersonaState",
    "QuestionType",
    "RecommendedAction",
    "Register",
    "RelationshipStage",
    "RelationshipState",
    "RiskLevel",
    "ScoredMemory",
    "SelfDisclosureDepth",
    "SemanticDraft",
    "SentenceLength",
    "SessionSummary",
    "TargetResponseLength",
    "UWMContextSnapshot",
    "VocabularyTier",
    "VoiceParameters",
]
