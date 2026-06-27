"""Tests for SC-6 Conversation Mode Resolver (architecture doc §8)."""

from backend.layer3_reasoning import mode_resolver as mr
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


def _resolve(emotion, intent, *, bes=None, mismatch=None):
    return mr.resolve_conversation_mode(
        primary_emotion=emotion,
        background_state=bes or BackgroundEmotionalState(),
        intent=intent,
        mismatch=mismatch or MismatchResult(mismatch_detected=False),
    )


def test_crisis_always_wins():
    mode = _resolve(EmotionClassification(crisis_flag=True, crisis_confidence=0.9, valence=-0.9),
                    IntentClassification(primary_intent=IntentLabel.SHARING_GOOD_NEWS.value))
    assert mode == ConversationMode.CRISIS.value


def test_high_arousal_negative_is_emotional_support():
    mode = _resolve(EmotionClassification(valence=-0.6, arousal=0.7),
                    IntentClassification(primary_intent=IntentLabel.CASUAL_CHAT.value))
    assert mode == ConversationMode.EMOTIONAL_SUPPORT.value


def test_mismatch_with_negative_bes_is_emotional_support():
    mode = _resolve(
        EmotionClassification(valence=0.2, arousal=0.3),
        IntentClassification(primary_intent=IntentLabel.CASUAL_CHAT.value),
        bes=BackgroundEmotionalState(bes_label=BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value),
        mismatch=MismatchResult(mismatch_detected=True))
    assert mode == ConversationMode.EMOTIONAL_SUPPORT.value


def test_celebration():
    mode = _resolve(
        EmotionClassification(primary_label=EmotionLabel.JOY.value, valence=0.8, arousal=0.6),
        IntentClassification(primary_intent=IntentLabel.SHARING_GOOD_NEWS.value))
    assert mode == ConversationMode.CELEBRATION.value


def test_technical_discussion():
    mode = _resolve(
        EmotionClassification(primary_label=EmotionLabel.NEUTRAL.value, valence=0.0),
        IntentClassification(primary_intent=IntentLabel.SEEKING_INFORMATION.value,
                             topic_domain=TopicDomain.ACADEMICS.value))
    assert mode == ConversationMode.TECHNICAL_DISCUSSION.value


def test_goal_planning():
    mode = _resolve(EmotionClassification(valence=0.1),
                    IntentClassification(primary_intent=IntentLabel.GOAL_SETTING.value))
    assert mode == ConversationMode.GOAL_PLANNING.value


def test_social_coaching():
    mode = _resolve(EmotionClassification(valence=0.0),
                    IntentClassification(primary_intent=IntentLabel.SEEKING_ADVICE.value,
                                         topic_domain=TopicDomain.RELATIONSHIPS.value))
    assert mode == ConversationMode.SOCIAL_COACHING.value


def test_life_review_from_reflection():
    mode = _resolve(EmotionClassification(valence=0.1),
                    IntentClassification(primary_intent=IntentLabel.REQUESTING_REFLECTION.value))
    assert mode == ConversationMode.LIFE_REVIEW.value


def test_casual_default():
    mode = _resolve(EmotionClassification(primary_label=EmotionLabel.NEUTRAL.value, valence=0.05),
                    IntentClassification(primary_intent=IntentLabel.CASUAL_CHAT.value))
    assert mode == ConversationMode.CASUAL.value


def test_emotional_support_precedes_technical_even_for_academics():
    # A distressed academic message routes to support, not technical discussion.
    mode = _resolve(
        EmotionClassification(valence=-0.6, arousal=0.7),
        IntentClassification(primary_intent=IntentLabel.SEEKING_INFORMATION.value,
                             topic_domain=TopicDomain.ACADEMICS.value))
    assert mode == ConversationMode.EMOTIONAL_SUPPORT.value
