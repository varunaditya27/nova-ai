"""Tests for SC-3 Intent Classifier (architecture doc §5)."""

from backend.layer3_reasoning import intent_classifier as ic
from backend.layer3_reasoning.schemas import (
    ClassificationMethod,
    IntentLabel,
    LLMClassificationOutput,
    TopicDomain,
)


# ── Rule layer (§5.3) ────────────────────────────────────────────────────────
def test_rule_factual_question_is_information_seeking():
    result = ic.rule_classify("what time is the exam tomorrow?")
    assert result is not None
    label, conf = result
    assert label == IntentLabel.SEEKING_INFORMATION.value
    assert conf >= 0.70


def test_rule_can_you_help_is_advice():
    result = ic.rule_classify("can you help me plan my week?")
    assert result is not None
    assert result[0] == IntentLabel.SEEKING_ADVICE.value


def test_rule_explicit_venting_marker():
    result = ic.rule_classify("I just need to vent for a second")
    assert result is not None
    assert result[0] == IntentLabel.VENTING.value
    assert result[1] >= 0.90


def test_rule_update_closing_a_loop():
    result = ic.rule_classify("btw turns out I got the apartment")
    assert result is not None
    assert result[0] == IntentLabel.PROVIDING_UPDATE.value


def test_rule_ambiguous_returns_none():
    assert ic.rule_classify("I don't know what to do about any of this") is None


# ── prefers_no_advice (§5.4) ─────────────────────────────────────────────────
def test_prefers_no_advice_explicit_statement():
    assert ic.compute_prefers_no_advice(
        "please don't give me advice, I just need to talk",
        IntentLabel.VENTING.value) is True


def test_prefers_no_advice_venting_without_question():
    assert ic.compute_prefers_no_advice(
        "work was exhausting and my manager was awful today",
        IntentLabel.VENTING.value) is True


def test_venting_with_question_does_not_force_no_advice():
    assert ic.compute_prefers_no_advice(
        "work was awful, what should I even do?",
        IntentLabel.VENTING.value) is False


def test_prefers_no_advice_long_validation_unloading():
    long_msg = "so much happened " * 60  # 180 words, > 150
    assert ic.compute_prefers_no_advice(
        long_msg, IntentLabel.SEEKING_VALIDATION.value) is True


def test_prefers_no_advice_from_uwm_history():
    assert ic.compute_prefers_no_advice(
        "here's what's going on", IntentLabel.PROVIDING_UPDATE.value,
        advice_frustration_count=3) is True


# ── classify_intent orchestration (§5.3) ─────────────────────────────────────
def test_classify_uses_rule_when_confident():
    intent = ic.classify_intent("what is the deadline?")
    assert intent.primary_intent == IntentLabel.SEEKING_INFORMATION.value
    assert intent.classification_method == ClassificationMethod.HEURISTIC_ONLY.value


def test_classify_falls_back_to_llm_when_ambiguous():
    def fake_llm(msg):
        return LLMClassificationOutput(
            primary_intent="decision_support", intent_confidence=0.8,
            needs_advice=True, topic_domain="career")

    intent = ic.classify_intent("I can't decide between the two offers", llm_fn=fake_llm)
    assert intent.primary_intent == IntentLabel.DECISION_SUPPORT.value
    assert intent.topic_domain == TopicDomain.CAREER.value
    assert intent.classification_method == ClassificationMethod.LLM_ONLY.value


def test_classify_without_llm_defaults_casual_for_ambiguous():
    intent = ic.classify_intent("hmm I really am not sure about all of this")
    assert intent.primary_intent == IntentLabel.CASUAL_CHAT.value
    assert intent.classification_method == ClassificationMethod.HEURISTIC_ONLY.value


def test_classify_overlays_prefers_no_advice_on_llm_result():
    def fake_llm(msg):
        return LLMClassificationOutput(
            primary_intent="venting", intent_confidence=0.7, prefers_no_advice=False)

    intent = ic.classify_intent("everything at home has been so heavy lately",
                                llm_fn=fake_llm)
    assert intent.primary_intent == IntentLabel.VENTING.value
    assert intent.prefers_no_advice is True   # overlaid by §5.4 rule (venting, no '?')
