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

Split by sub-component into submodules; this ``__init__`` re-exports everything so
``from backend.layer3_reasoning.schemas import X`` keeps working unchanged.
"""

from __future__ import annotations

# Canonical types owned upstream (single source of truth).
from backend.layer2_memory.schemas import ConversationMode, EmotionVector

from .background_state import BackgroundEmotionalState, BESLabel
from .empathy import DisclosureDepth, EmpathyHypothesis, PrimaryNeed, ResponsePosture
from .emotion import (
    ClassificationMethod,
    CrisisType,
    EMOTION_TAXONOMY,
    EmotionClassification,
    EmotionLabel,
    LLMClassificationOutput,
    SecondaryEmotion,
)
from .intent import IntentClassification, IntentLabel, TopicDomain
from .mismatch import MismatchPosture, MismatchResult, MismatchType
from .packet import AdviceGate, CrisisAlert, EmotionIntentPacket, ResponsePacing

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
