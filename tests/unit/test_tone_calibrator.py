"""Tests for SC-3 Tone & Style Calibrator (architecture doc §5)."""

from backend.layer4_persona import tone_calibrator as tc
from backend.layer4_persona.schemas import (
    HumorMode,
    PersonaState,
    Register,
    RelationshipStage,
    RelationshipState,
    VocabularyTier,
    VoiceParameters,
)
from backend.layer2_memory.schemas import ConversationMode
from backend.layer3_reasoning.schemas import BackgroundEmotionalState, BESLabel


def _rel(stage=RelationshipStage.DEVELOPING.value, **kw):
    base = dict(stage=stage, question_tolerance=0.6, response_length_preference=0.5,
                formality_preference=0.5, follow_up_question_ceiling=3,
                self_disclosure_ceiling="moderate")
    base.update(kw)
    return RelationshipState(**base)


def _persona(**kw):
    base = dict(humor_allowed=True, technical_depth_allowed=True)
    base.update(kw)
    return PersonaState(**base)


def _calibrate(mode, *, band="afternoon", rel=None, persona=None, bes=None):
    return tc.calibrate_voice(
        conversation_mode=mode, circadian_band=band,
        relationship_state=rel or _rel(), persona_state=persona or _persona(),
        background_state=bes or BackgroundEmotionalState())


# ── Mode base parameters (§5.3 Input 1) ──────────────────────────────────────
def test_crisis_mode_base_parameters():
    v = _calibrate(ConversationMode.CRISIS.value)
    assert v.register == Register.NATURAL.value
    assert v.humor_mode == HumorMode.NONE.value
    assert v.validation_first is True
    assert v.warmth_expression >= 0.85
    assert v.opinion_expression_allowed is False


def test_technical_mode_uses_lists_and_technical_vocab():
    v = _calibrate(ConversationMode.TECHNICAL_DISCUSSION.value)
    assert v.use_lists is True
    assert v.vocabulary_tier == VocabularyTier.TECHNICAL.value


# ── Circadian adjustment (§5.3 Input 2) ──────────────────────────────────────
def test_late_night_shortens_warms_and_suppresses_humor():
    day = _calibrate(ConversationMode.CASUAL.value, band="afternoon")
    night = _calibrate(ConversationMode.CASUAL.value, band="late_night")
    assert night.warmth_expression > day.warmth_expression
    assert night.humor_mode == HumorMode.NONE.value
    assert night.max_response_length_chars < day.max_response_length_chars


# ── BES negative drift override (§5.3 Input 5) ───────────────────────────────
def test_bes_negative_drift_warms_and_suppresses_humor():
    neutral = _calibrate(ConversationMode.CASUAL.value)
    drift = _calibrate(ConversationMode.CASUAL.value,
                       bes=BackgroundEmotionalState(bes_label=BESLabel.DETERIORATING.value))
    assert drift.warmth_expression > neutral.warmth_expression
    assert drift.humor_mode == HumorMode.NONE.value
    assert drift.max_response_length_chars < neutral.max_response_length_chars


# ── Persona hard constraints applied last (§5.3 final assembly) ──────────────
def test_persona_humor_disallowed_forces_none_even_in_celebration():
    v = _calibrate(ConversationMode.CELEBRATION.value, persona=_persona(humor_allowed=False))
    assert v.humor_mode == HumorMode.NONE.value


def test_persona_no_technical_depth_forces_standard_vocab():
    v = _calibrate(ConversationMode.TECHNICAL_DISCUSSION.value,
                   persona=_persona(technical_depth_allowed=False))
    assert v.vocabulary_tier == VocabularyTier.STANDARD.value


def test_low_question_tolerance_disables_followups():
    v = _calibrate(ConversationMode.CASUAL.value, rel=_rel(question_tolerance=0.2))
    assert v.follow_up_question_allowed is False
    assert v.follow_up_question_max == 0


# ── Relationship stage register override (§5.3 Input 3) ──────────────────────
def test_new_stage_register_more_formal_than_close():
    new = _calibrate(ConversationMode.CASUAL.value, rel=_rel(stage=RelationshipStage.NEW.value))
    close = _calibrate(ConversationMode.CASUAL.value, rel=_rel(stage=RelationshipStage.CLOSE.value))
    assert new.register == Register.PROFESSIONAL.value
    assert close.register == Register.INTIMATE.value


def test_crisis_register_stays_natural_regardless_of_stage():
    v = _calibrate(ConversationMode.CRISIS.value, rel=_rel(stage=RelationshipStage.CLOSE.value))
    assert v.register == Register.NATURAL.value


# ── Follow-up ceiling from relationship stage (§4.4 gate) ────────────────────
def test_followups_capped_by_relationship_ceiling():
    # celebration mode permits 2 questions, but a new-stage user caps at 1.
    v = _calibrate(ConversationMode.CELEBRATION.value,
                   rel=_rel(stage=RelationshipStage.NEW.value, follow_up_question_ceiling=1))
    assert v.follow_up_question_max <= 1


# ── User length preference (§5.3 Input 4) ────────────────────────────────────
def test_high_length_preference_expands_max_chars():
    short = _calibrate(ConversationMode.CASUAL.value, rel=_rel(response_length_preference=0.1))
    long = _calibrate(ConversationMode.CASUAL.value, rel=_rel(response_length_preference=0.9))
    assert long.max_response_length_chars > short.max_response_length_chars


# ── Self-disclosure gated by stage (§4.4 / §5.2) ─────────────────────────────
def test_self_disclosure_gated_by_relationship_stage():
    new = _calibrate(ConversationMode.EMOTIONAL_SUPPORT.value,
                     rel=_rel(stage=RelationshipStage.NEW.value, self_disclosure_ceiling="surface"))
    established = _calibrate(ConversationMode.EMOTIONAL_SUPPORT.value,
                            rel=_rel(stage=RelationshipStage.ESTABLISHED.value,
                                     self_disclosure_ceiling="moderate"))
    assert new.self_disclosure_allowed is False
    assert established.self_disclosure_allowed is True


# ── Robustness: every mode produces a valid VoiceParameters ──────────────────
def test_all_modes_produce_valid_voice_parameters():
    for mode in ConversationMode:
        v = _calibrate(mode.value)
        assert isinstance(v, VoiceParameters)
        assert 0.0 <= v.warmth_expression <= 1.0
        assert v.max_response_length_chars >= 200
