"""Layer 3 — Emotion, Intent & Reasoning (architecture doc §1–§9).

The interpretive core of the pipeline: it reads meaning, not just text. Every upstream
signal (the Layer 1 circadian prior, implicit intensity, prosody; the Layer 2 recalled
memories and User World Model) converges here and is synthesised into a single read-only
``EmotionIntentPacket`` that governs everything downstream — how Nova speaks, what it says,
in what order, and with what emotional posture.

Central claim: getting the emotion right and the content wrong is recoverable; getting the
content right and the emotion wrong is not.

Six sub-components in two groups:
  Classification group:
    - emotion_classifier  (SC-1) — heuristic + LLM + prior integration
    - background_state    (SC-2) — 14-day emotional drift from Layer 2 data
    - intent_classifier   (SC-3) — rule-first, LLM-fallback; prefers_no_advice hard rule
    - mismatch_detector   (SC-4) — stated-vs-felt gap → response posture
  Reasoning group:
    - empathy_hypothesis  (SC-5) — auditable need/posture synthesis
    - mode_resolver       (SC-6) — deterministic ConversationMode

  packet_builder — orchestrates SC-1..SC-6 into the EmotionIntentPacket, translates scores
                   into plain-language LLM instructions (§9.1), and guarantees the §12 hard
                   rules (crisis alert emitted before any fallible work; always emit a packet).

Note: response *generation* (Semantic Planner 4a / Emotion Refiner 4b) lives in Layer 4,
not here — see architecture doc §11. The earlier scaffold placed those stubs in this
package; they have been relocated to keep Layer 3 read-only and classification-only.
"""

from backend.layer3_reasoning import (
    background_state,
    emotion_classifier,
    empathy_hypothesis,
    intent_classifier,
    mismatch_detector,
    mode_resolver,
    packet_builder,
    schemas,
)
from backend.layer3_reasoning.packet_builder import build_emotion_intent_packet
from backend.layer3_reasoning.schemas import (
    AdviceGate,
    BackgroundEmotionalState,
    BESLabel,
    ClassificationMethod,
    ConversationMode,
    CrisisAlert,
    CrisisType,
    DisclosureDepth,
    EmotionClassification,
    EmotionIntentPacket,
    EmotionLabel,
    EmotionVector,
    EmpathyHypothesis,
    IntentClassification,
    IntentLabel,
    LLMClassificationOutput,
    MismatchPosture,
    MismatchResult,
    MismatchType,
    PrimaryNeed,
    ResponsePacing,
    ResponsePosture,
    SecondaryEmotion,
    TopicDomain,
)

__all__ = [
    # Submodules.
    "schemas",
    "emotion_classifier",
    "background_state",
    "intent_classifier",
    "mismatch_detector",
    "empathy_hypothesis",
    "mode_resolver",
    "packet_builder",
    # Primary entry point.
    "build_emotion_intent_packet",
    # Key types.
    "EmotionIntentPacket",
    "EmotionClassification",
    "BackgroundEmotionalState",
    "IntentClassification",
    "MismatchResult",
    "EmpathyHypothesis",
    "CrisisAlert",
    "EmotionVector",
    "ConversationMode",
    "EmotionLabel",
    "BESLabel",
    "IntentLabel",
    "TopicDomain",
    "MismatchType",
    "MismatchPosture",
    "PrimaryNeed",
    "ResponsePosture",
    "DisclosureDepth",
    "AdviceGate",
    "ResponsePacing",
    "CrisisType",
    "ClassificationMethod",
    "SecondaryEmotion",
    "LLMClassificationOutput",
]
