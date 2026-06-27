"""SC-6 — Conversation Mode Resolver (architecture doc §8).

The last and simplest step of Layer 3: a deterministic policy that collapses every
classification output into a single authoritative ``conversation_mode``. That label governs
Layer 2 context gating, the Semantic Planner's constraints, the Emotion Refiner's depth,
and Layer 9 pacing. Order matters — earlier rules win (crisis is unconditional).
"""

from __future__ import annotations

from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    BESLabel,
    ConversationMode,
    EmotionClassification,
    EmotionLabel,
    IntentClassification,
    IntentLabel,
    MismatchResult,
    TopicDomain,
)

_NEGATIVE_BES = {BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value, BESLabel.DETERIORATING.value}


def resolve_conversation_mode(
    primary_emotion: EmotionClassification,
    background_state: BackgroundEmotionalState,
    intent: IntentClassification,
    mismatch: MismatchResult,
) -> str:
    """Resolve the single governing conversation mode (architecture doc §8.2)."""
    # Crisis always wins; no override possible.
    if primary_emotion.crisis_flag and primary_emotion.crisis_confidence > 0.65:
        return ConversationMode.CRISIS.value

    # High-arousal negative emotion → emotional support.
    if primary_emotion.valence < -0.4 and primary_emotion.arousal > 0.5:
        return ConversationMode.EMOTIONAL_SUPPORT.value

    # A mismatch against a negative background → support regardless of stated content.
    if mismatch.mismatch_detected and background_state.bes_label in _NEGATIVE_BES:
        return ConversationMode.EMOTIONAL_SUPPORT.value

    # Celebration.
    if (primary_emotion.primary_label in (EmotionLabel.JOY.value, EmotionLabel.PRIDE.value)
            and intent.primary_intent == IntentLabel.SHARING_GOOD_NEWS.value):
        return ConversationMode.CELEBRATION.value

    # Technical / informational.
    if (intent.topic_domain in (TopicDomain.ACADEMICS.value, TopicDomain.CAREER.value)
            and intent.primary_intent in (IntentLabel.SEEKING_INFORMATION.value,
                                          IntentLabel.PROBLEM_SOLVING.value)
            and primary_emotion.valence > -0.2):
        return ConversationMode.TECHNICAL_DISCUSSION.value

    # Goal planning.
    if intent.primary_intent in (IntentLabel.GOAL_SETTING.value,
                                 IntentLabel.DECISION_SUPPORT.value):
        return ConversationMode.GOAL_PLANNING.value

    # Social coaching.
    if intent.topic_domain == TopicDomain.RELATIONSHIPS.value:
        return ConversationMode.SOCIAL_COACHING.value

    # Life review (explicit reflection or closing a loop).
    if intent.primary_intent in (IntentLabel.REQUESTING_REFLECTION.value,
                                 IntentLabel.PROVIDING_UPDATE.value):
        return ConversationMode.LIFE_REVIEW.value

    return ConversationMode.CASUAL.value
