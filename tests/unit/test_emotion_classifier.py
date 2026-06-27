"""Tests for SC-1 Primary Emotion Classifier (architecture doc §3)."""

import math

from backend.layer3_reasoning import emotion_classifier as ec
from backend.layer3_reasoning.schemas import (
    ClassificationMethod,
    EmotionClassification,
    LLMClassificationOutput,
)
from backend.layer1_input.schemas import ProsodyEmotionEstimate


# ── Heuristic pre-filter: crisis (§3.3) ──────────────────────────────────────
def test_crisis_keyword_triggers_crisis_flag():
    clf = ec.heuristic_prefilter("honestly I just want to die", implicit_intensity=0.9,
                                 circadian_band="late_night")
    assert clf is not None
    assert clf.crisis_flag is True
    assert clf.crisis_confidence >= 0.9
    assert clf.primary_label == "despair"
    assert clf.crisis_type == "suicidal_ideation"


def test_self_harm_keyword_classified_as_self_harm_type():
    clf = ec.heuristic_prefilter("I want to hurt myself", implicit_intensity=0.8,
                                 circadian_band="late_night")
    assert clf is not None
    assert clf.crisis_flag is True
    assert clf.crisis_type == "self_harm_ideation"


def test_celebration_pattern_low_implicit_is_joy():
    clf = ec.heuristic_prefilter("I got the job!!", implicit_intensity=0.1,
                                 circadian_band="afternoon")
    assert clf is not None
    assert clf.primary_label == "joy"
    assert clf.valence > 0.5
    assert clf.crisis_flag is False


def test_neutral_informational_message_short_circuits():
    clf = ec.heuristic_prefilter("the meeting is at noon", implicit_intensity=0.05,
                                 circadian_band="afternoon")
    assert clf is not None
    assert clf.primary_label == "neutral"


def test_ambiguous_message_returns_none():
    clf = ec.heuristic_prefilter("I don't know how I feel about all this lately",
                                 implicit_intensity=0.5, circadian_band="evening")
    assert clf is None


# ── remap_label (§3.4) ───────────────────────────────────────────────────────
def test_remap_label_picks_nearest_taxonomy_centroid():
    # Strongly negative + high arousal → the activated-distress cluster, not neutral
    label = ec.remap_label(valence=-0.6, arousal=0.8, fallback="neutral")
    assert label in ("anxiety", "anger", "overwhelm")


def test_remap_label_positive_calm_is_contentment_region():
    label = ec.remap_label(valence=0.5, arousal=0.2, fallback="neutral")
    assert label in ("contentment", "relief")


# ── Prior integration (§3.4) ─────────────────────────────────────────────────
def test_prior_shifts_valence_negative_when_vulnerable():
    raw = LLMClassificationOutput(primary_label="neutral", valence=0.0, arousal=0.2,
                                  confidence=0.7)
    clf = ec.integrate_prior(raw, composite_prior=0.8, prior_confidence=0.9)
    assert clf.valence < 0.0          # shifted toward negative
    assert clf.arousal > 0.2          # arousal slightly elevated
    assert clf.prior_was_applied is True
    assert clf.classification_method == ClassificationMethod.LLM_PLUS_PRIOR.value


def test_low_prior_confidence_leaves_llm_result_intact():
    raw = LLMClassificationOutput(primary_label="joy", valence=0.7, arousal=0.6,
                                  confidence=0.8)
    clf = ec.integrate_prior(raw, composite_prior=0.9, prior_confidence=0.2)
    assert math.isclose(clf.valence, 0.7, abs_tol=1e-9)
    assert clf.prior_was_applied is False
    assert clf.classification_method == ClassificationMethod.LLM_ONLY.value


def test_prosody_override_blends_when_conflicting_and_confident():
    raw = LLMClassificationOutput(primary_label="neutral", valence=0.5, arousal=0.3,
                                  confidence=0.7)
    prosody = ProsodyEmotionEstimate(valence=-0.5, arousal=0.8, confidence=0.85)
    clf = ec.integrate_prior(raw, composite_prior=0.0, prior_confidence=0.0,
                             prosody_estimate=prosody)
    # 60% LLM (0.5) + 40% prosody (-0.5) = 0.1
    assert math.isclose(clf.valence, 0.1, abs_tol=1e-9)


def test_integrate_prior_clamps_to_valid_ranges():
    raw = LLMClassificationOutput(valence=-0.95, arousal=0.95, confidence=0.9)
    clf = ec.integrate_prior(raw, composite_prior=0.95, prior_confidence=1.0)
    assert -1.0 <= clf.valence <= 1.0
    assert 0.0 <= clf.arousal <= 1.0


# ── classify_emotion orchestration (§3.3, §12) ───────────────────────────────
def test_classify_uses_heuristic_only_for_neutral_without_llm():
    clf = ec.classify_emotion("the file is in the folder", implicit_intensity=0.05,
                              circadian_band="afternoon")
    assert clf.primary_label == "neutral"
    assert clf.classification_method == ClassificationMethod.HEURISTIC_ONLY.value


def test_classify_invokes_llm_for_ambiguous_message():
    calls = []

    def fake_llm(msg):
        calls.append(msg)
        return LLMClassificationOutput(primary_label="anxiety", valence=-0.5, arousal=0.7,
                                       confidence=0.8)

    clf = ec.classify_emotion("I really don't know what to do anymore about everything",
                              implicit_intensity=0.5, circadian_band="late_night",
                              composite_prior=0.7, prior_confidence=0.8, llm_fn=fake_llm)
    assert len(calls) == 1
    assert clf.primary_label in ("anxiety", "sadness", "despair", "overwhelm")
    assert clf.classification_method == ClassificationMethod.LLM_PLUS_PRIOR.value


def test_classify_preserves_crisis_from_heuristic_even_with_llm():
    def calm_llm(msg):
        return LLMClassificationOutput(primary_label="sadness", valence=-0.4, arousal=0.3,
                                       confidence=0.6, crisis_flag=False)

    clf = ec.classify_emotion("I can't go on like this, I want to die",
                              implicit_intensity=0.9, circadian_band="late_night",
                              llm_fn=calm_llm)
    assert clf.crisis_flag is True
    assert clf.crisis_confidence >= 0.9


def test_classify_without_llm_caps_confidence_for_ambiguous():
    # No llm_fn and ambiguous message → degraded heuristic_only, capped confidence.
    clf = ec.classify_emotion("ugh everything is just a lot right now and I can't",
                              implicit_intensity=0.6, circadian_band="late_night")
    assert clf.classification_method == ClassificationMethod.HEURISTIC_ONLY.value
    assert clf.confidence <= 0.65


# ── EmotionClassification derived fields (§3.5) ──────────────────────────────
def test_intensity_is_normalised_magnitude():
    clf = EmotionClassification(valence=1.0, arousal=1.0)
    assert math.isclose(clf.intensity, 1.0, abs_tol=1e-9)
    calm = EmotionClassification(valence=0.0, arousal=0.0)
    assert math.isclose(calm.intensity, 0.0, abs_tol=1e-9)


def test_emotion_vector_property_matches_fields():
    clf = EmotionClassification(valence=-0.3, arousal=0.6)
    assert clf.emotion_vector.valence == -0.3
    assert clf.emotion_vector.arousal == 0.6
