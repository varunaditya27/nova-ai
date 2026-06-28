"""Tests for SC-2 Initiative Classifier (architecture doc §4)."""

from backend.layer6_proactivity import initiative_classifier as ic
from backend.layer6_proactivity.schemas import (
    ClassifiedInitiative,
    InitiativeType,
    ProactiveItem,
    ProactiveItemType,
    QuestionType,
)


def _item(item_type, **kw):
    return ProactiveItem(item_type=item_type, content_basis="x" * 40, **kw)


def _classify(item, bes="stable", stage="developing", gap=2):
    return ic.classify_initiative(item, bes_trend=bes, relationship_stage=stage,
                                  session_gap_days=gap)


# ── Reconnection opener overrides everything on long silence (§4.3) ──────────
def test_long_silence_is_reconnection_opener():
    c = _classify(_item(ProactiveItemType.EMOTIONAL_CHECK_IN.value), gap=30)
    assert c.initiative_type == InitiativeType.RECONNECTION_OPENER.value
    assert c.reference_depth == "minimal"


# ── Emotional check-in branches (§4.3) ───────────────────────────────────────
def test_emotional_checkin_deteriorating_is_concerned():
    c = _classify(_item(ProactiveItemType.EMOTIONAL_CHECK_IN.value), bes="deteriorating")
    assert c.initiative_type == InitiativeType.CONCERNED_CHECK_IN.value
    assert c.emotional_register == "warm_direct"
    assert c.reference_depth == "specific"


def test_emotional_checkin_stable_is_caring():
    c = _classify(_item(ProactiveItemType.EMOTIONAL_CHECK_IN.value), bes="stable")
    assert c.initiative_type == InitiativeType.CARING_CHECK_IN.value
    assert c.reference_depth == "vague"


# ── Thread / upcoming-date branches (§4.3) ───────────────────────────────────
def test_positive_anticipation_is_celebratory():
    c = _classify(_item(ProactiveItemType.THREAD_FOLLOW_UP.value, content_basis_valence=0.6))
    assert c.initiative_type == InitiativeType.CELEBRATORY_FOLLOW_UP.value
    assert c.emotional_register == "warm_energetic"


def test_non_positive_anticipation_is_curious():
    c = _classify(_item(ProactiveItemType.UPCOMING_DATE_REMINDER.value, content_basis_valence=0.0))
    assert c.initiative_type == InitiativeType.CURIOUS_FOLLOW_UP.value


def test_missing_valence_defaults_to_curious_not_crash():
    c = _classify(_item(ProactiveItemType.THREAD_FOLLOW_UP.value, content_basis_valence=None))
    assert c.initiative_type == InitiativeType.CURIOUS_FOLLOW_UP.value


# ── Gentle nudge for goal / coaching (§4.3) ──────────────────────────────────
def test_goal_and_coaching_are_gentle_nudge():
    for t in (ProactiveItemType.GOAL_CHECK_IN.value,
              ProactiveItemType.SOCIAL_PATTERN_COACHING.value,
              ProactiveItemType.RELATIONSHIP_CHECK_IN.value):
        c = _classify(_item(t))
        assert c.initiative_type == InitiativeType.GENTLE_NUDGE.value
        assert c.content_framing == "invitational"


# ── Default caring check-in (§4.3) ───────────────────────────────────────────
def test_default_is_caring_check_in():
    c = _classify(_item(ProactiveItemType.WELLBEING_CHECK.value))
    assert c.initiative_type == InitiativeType.CARING_CHECK_IN.value


# ── Delivery parameters set (§4.4) ───────────────────────────────────────────
def test_classified_sets_length_and_question_fields():
    c = _classify(_item(ProactiveItemType.THREAD_FOLLOW_UP.value, content_basis_valence=0.6))
    assert isinstance(c, ClassifiedInitiative)
    assert c.max_length_chars > 0
    assert isinstance(c.include_question, bool)
    assert c.question_type in {q.value for q in QuestionType}
