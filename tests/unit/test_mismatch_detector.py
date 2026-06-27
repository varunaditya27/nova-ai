"""Tests for SC-4 Stated-vs-Felt Mismatch Detector (architecture doc §6)."""

from backend.layer3_reasoning import mismatch_detector as md
from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    BESLabel,
    EmotionClassification,
    MismatchPosture,
    MismatchType,
)


def _emotion(valence):
    return EmotionClassification(valence=valence, arousal=0.4)


def _bes(label=BESLabel.STABLE_NEUTRAL.value):
    return BackgroundEmotionalState(bes_label=label)


# ── Detection logic (§6.2) ───────────────────────────────────────────────────
def test_masking_detected_positive_stated_negative_felt():
    res = md.detect_mismatch(_emotion(0.4), composite_prior=0.85, implicit_intensity=0.7,
                             prosody_estimate=None, signal_mismatch_flag=False,
                             message="I'm great, really!", background_state=_bes())
    assert res.mismatch_detected is True
    assert res.mismatch_type == MismatchType.MASKING.value


def test_minimizing_detected_neutral_stated_negative_felt():
    res = md.detect_mismatch(_emotion(0.0), composite_prior=0.75, implicit_intensity=0.6,
                             prosody_estimate=None, signal_mismatch_flag=False,
                             message="it's been a day", background_state=_bes())
    assert res.mismatch_detected is True
    assert res.mismatch_type == MismatchType.MINIMIZING.value


def test_no_mismatch_when_stated_and_felt_aligned():
    res = md.detect_mismatch(_emotion(-0.7), composite_prior=0.85, implicit_intensity=0.7,
                             prosody_estimate=None, signal_mismatch_flag=False,
                             message="I feel awful", background_state=_bes())
    assert res.mismatch_detected is False


def test_deflection_with_negative_bes_triggers_even_small_gap():
    res = md.detect_mismatch(_emotion(0.05), composite_prior=0.3, implicit_intensity=0.2,
                             prosody_estimate=None, signal_mismatch_flag=False,
                             message="I'm fine, don't worry about it",
                             background_state=_bes(BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value))
    assert res.mismatch_detected is True
    assert "I'm fine" in res.deflection_phrases_detected


def test_signal_mismatch_flag_forces_detection():
    res = md.detect_mismatch(_emotion(0.1), composite_prior=0.2, implicit_intensity=0.1,
                             prosody_estimate=None, signal_mismatch_flag=True,
                             message="all good here", background_state=_bes())
    assert res.mismatch_detected is True


def test_linguistic_hedging_type_when_multiple_hedges():
    res = md.detect_mismatch(_emotion(-0.15), composite_prior=0.7, implicit_intensity=0.4,
                             prosody_estimate=None, signal_mismatch_flag=False,
                             message="I guess it's kind of fine, sort of",
                             background_state=_bes())
    assert res.mismatch_detected is True
    assert res.mismatch_type == MismatchType.LINGUISTIC_HEDGING.value
    assert len(res.hedging_phrases_detected) >= 2


def test_confidence_rises_with_magnitude_and_deflections():
    res = md.detect_mismatch(_emotion(0.6), composite_prior=0.9, implicit_intensity=0.8,
                             prosody_estimate=None, signal_mismatch_flag=False,
                             message="I'm fine, all good, not a big deal",
                             background_state=_bes())
    assert res.mismatch_confidence > 0.6


# ── Posture selection (§6.3 table) ───────────────────────────────────────────
def test_posture_direct_noticing_for_deep_confident_masking():
    posture = md.select_mismatch_posture(MismatchType.MASKING.value,
                                         relationship_depth=0.7, confidence=0.85)
    assert posture == MismatchPosture.DIRECT_NOTICING.value


def test_posture_hold_and_watch_for_new_relationship():
    posture = md.select_mismatch_posture(MismatchType.MASKING.value,
                                         relationship_depth=0.2, confidence=0.9)
    assert posture == MismatchPosture.HOLD_AND_WATCH.value


def test_posture_hold_and_watch_for_low_confidence():
    posture = md.select_mismatch_posture(MismatchType.MINIMIZING.value,
                                         relationship_depth=0.7, confidence=0.4)
    assert posture == MismatchPosture.HOLD_AND_WATCH.value


def test_posture_gentle_acknowledgment_default():
    posture = md.select_mismatch_posture(MismatchType.MINIMIZING.value,
                                         relationship_depth=0.5, confidence=0.7)
    assert posture == MismatchPosture.GENTLE_ACKNOWLEDGMENT.value


def test_detect_mismatch_attaches_posture():
    res = md.detect_mismatch(_emotion(0.4), composite_prior=0.85, implicit_intensity=0.7,
                             prosody_estimate=None, signal_mismatch_flag=False,
                             message="I'm great!", background_state=_bes(),
                             relationship_depth=0.7)
    assert res.mismatch_response_posture is not None
