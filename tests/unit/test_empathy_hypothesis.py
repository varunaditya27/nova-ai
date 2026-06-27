"""Tests for SC-5 Empathy Hypothesis Generator (architecture doc §7)."""

from backend.layer3_reasoning import empathy_hypothesis as eh
from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    BESLabel,
    DisclosureDepth,
    EmotionClassification,
    EmotionLabel,
    IntentClassification,
    IntentLabel,
    MismatchResult,
    PrimaryNeed,
    ResponsePosture,
)
from backend.layer2_memory.schemas import PsychologicalModel


def _intent(label, **kw):
    return IntentClassification(primary_intent=label, **kw)


def _bes(label=BESLabel.STABLE_NEUTRAL.value):
    return BackgroundEmotionalState(bes_label=label)


def _no_mismatch():
    return MismatchResult(mismatch_detected=False)


# ── Intent/emotion → need (§7.3) ─────────────────────────────────────────────
def test_venting_maps_to_be_heard():
    assert eh.map_intent_emotion_to_need(
        IntentLabel.VENTING.value, EmotionClassification(valence=-0.4)) == PrimaryNeed.TO_BE_HEARD.value


def test_good_news_maps_to_celebrate():
    assert eh.map_intent_emotion_to_need(
        IntentLabel.SHARING_GOOD_NEWS.value,
        EmotionClassification(primary_label=EmotionLabel.JOY.value, valence=0.8)
    ) == PrimaryNeed.TO_CELEBRATE.value


def test_decision_support_maps_to_decide():
    assert eh.map_intent_emotion_to_need(
        IntentLabel.DECISION_SUPPORT.value, EmotionClassification()) == PrimaryNeed.TO_DECIDE.value


# ── Need → posture, with BES override (§7.4) ─────────────────────────────────
def test_to_decide_default_is_co_think():
    assert eh.map_need_to_posture(
        PrimaryNeed.TO_DECIDE.value, BESLabel.STABLE_NEUTRAL.value, 0.5
    ) == ResponsePosture.CO_THINK.value


def test_to_decide_under_negative_drift_becomes_validate_then_solve():
    assert eh.map_need_to_posture(
        PrimaryNeed.TO_DECIDE.value, BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value, 0.5
    ) == ResponsePosture.VALIDATE_THEN_SOLVE.value


def test_distraction_under_negative_drift_becomes_gentle_redirect():
    assert eh.map_need_to_posture(
        PrimaryNeed.DISTRACTION.value, BESLabel.DETERIORATING.value, 0.5
    ) == ResponsePosture.GENTLE_REDIRECT.value


# ── Full hypothesis generation (§7.3) ────────────────────────────────────────
def test_venting_hypothesis_withholds_advice():
    hyp = eh.generate_empathy_hypothesis(
        primary_emotion=EmotionClassification(valence=-0.4, arousal=0.5),
        background_state=_bes(), intent=_intent(IntentLabel.VENTING.value, prefers_no_advice=True),
        mismatch=_no_mismatch(), relationship_depth=0.5)
    assert hyp.primary_need == PrimaryNeed.TO_BE_HEARD.value
    assert hyp.response_posture == ResponsePosture.VALIDATE_THEN_HOLD.value
    assert hyp.advice_withheld is True


def test_crisis_forces_crisis_support_and_protocol():
    hyp = eh.generate_empathy_hypothesis(
        primary_emotion=EmotionClassification(crisis_flag=True, valence=-0.9),
        background_state=_bes(), intent=_intent(IntentLabel.SEEKING_INFORMATION.value),
        mismatch=_no_mismatch(), relationship_depth=0.8)
    assert hyp.primary_need == PrimaryNeed.CRISIS_SUPPORT.value
    assert hyp.response_posture == ResponsePosture.CRISIS_PROTOCOL.value
    assert hyp.is_crisis is True


def test_mismatch_overrides_need_to_be_heard():
    hyp = eh.generate_empathy_hypothesis(
        primary_emotion=EmotionClassification(valence=0.3),
        background_state=_bes(),
        intent=_intent(IntentLabel.SEEKING_INFORMATION.value),
        mismatch=MismatchResult(mismatch_detected=True, mismatch_confidence=0.8),
        relationship_depth=0.5)
    assert hyp.primary_need == PrimaryNeed.TO_BE_HEARD.value
    assert hyp.apply_mismatch_posture is True


def test_solution_oriented_preference_flips_hold_to_solve():
    psych = PsychologicalModel(preferred_support_style="solution_oriented")
    hyp = eh.generate_empathy_hypothesis(
        primary_emotion=EmotionClassification(valence=-0.3, arousal=0.4),
        background_state=_bes(), intent=_intent(IntentLabel.VENTING.value),
        mismatch=_no_mismatch(), relationship_depth=0.5, uwm_psychological=psych)
    assert hyp.response_posture == ResponsePosture.VALIDATE_THEN_SOLVE.value


def test_disclosure_depth_scales_with_relationship():
    surface = eh.generate_empathy_hypothesis(
        EmotionClassification(), _bes(), _intent(IntentLabel.CASUAL_CHAT.value),
        _no_mismatch(), relationship_depth=0.1)
    deep = eh.generate_empathy_hypothesis(
        EmotionClassification(), _bes(), _intent(IntentLabel.CASUAL_CHAT.value),
        _no_mismatch(), relationship_depth=0.8)
    assert surface.disclosure_depth_allowed == DisclosureDepth.SURFACE.value
    assert deep.disclosure_depth_allowed == DisclosureDepth.DEEP.value


def test_skip_refinement_for_neutral_no_drift_no_mismatch():
    hyp = eh.generate_empathy_hypothesis(
        EmotionClassification(primary_label=EmotionLabel.NEUTRAL.value),
        _bes(BESLabel.STABLE_NEUTRAL.value),
        _intent(IntentLabel.SEEKING_INFORMATION.value),
        _no_mismatch(), relationship_depth=0.3)
    assert hyp.skip_emotional_refinement is True


def test_no_skip_refinement_when_mismatch_present():
    hyp = eh.generate_empathy_hypothesis(
        EmotionClassification(primary_label=EmotionLabel.NEUTRAL.value),
        _bes(BESLabel.STABLE_NEUTRAL.value),
        _intent(IntentLabel.SEEKING_INFORMATION.value),
        MismatchResult(mismatch_detected=True, mismatch_confidence=0.7),
        relationship_depth=0.3)
    assert hyp.skip_emotional_refinement is False
