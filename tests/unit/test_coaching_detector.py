"""Tests for SC-4 Coaching Opportunity Detector (architecture doc §6)."""

from datetime import datetime, timedelta

from backend.layer5_relationship import coaching_detector as cd
from backend.layer5_relationship.schemas import (
    CoachingType,
    SocialEvent,
    SocialEventType,
    SocialGraph,
    SocialNode,
    SocialPattern,
    SocialPatternType,
)
from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    BESLabel,
    EmotionClassification,
    EmotionLabel,
)

NOW = datetime(2026, 6, 28)


def _pattern(**kw):
    base = dict(pattern_type=SocialPatternType.RECURRING_CONFLICT_TOPIC.value,
                person_ids_involved=["p1"], pattern_confidence=0.8, pattern_strength=0.5,
                plain_language_description="You've described conflict with Riya a few times.",
                coaching_hook="a recurring conflict theme with Riya",
                has_been_surfaced=False, last_activation=NOW, last_observed=NOW)
    base.update(kw)
    return SocialPattern(**base)


def _emotion(label=EmotionLabel.NEUTRAL.value, valence=0.0, crisis=False):
    return EmotionClassification(primary_label=label, valence=valence, crisis_flag=crisis)


def _graph(*nodes):
    return SocialGraph(nodes={n.person_id: n for n in nodes})


# ── Gate 1: availability (§6.4) ──────────────────────────────────────────────
def test_gate1_returns_unsurfaced_pattern():
    opp = cd.gate_1_availability([_pattern()], [], _graph(), now=NOW)
    assert opp is not None
    assert opp.triggering_pattern is not None
    assert opp.coaching_type is not None


def test_gate1_none_when_nothing_available():
    assert cd.gate_1_availability([], [], _graph(), now=NOW) is None


def test_gate1_priority_conflict_when_no_patterns():
    conflict = SocialEvent(person_id="p1", event_type=SocialEventType.CONFLICT_ONSET.value,
                           is_resolved=False, emotional_intensity=0.8, reported_timestamp=NOW)
    opp = cd.gate_1_availability([], [conflict], _graph(SocialNode(person_id="p1")), now=NOW)
    assert opp is not None
    assert opp.coaching_type == CoachingType.CONFLICT_NAVIGATION.value


def test_gate1_support_network_erosion():
    node = SocialNode(person_id="p1", display_name="Mom", is_support_source=True,
                      last_mentioned=NOW - timedelta(days=50))
    opp = cd.gate_1_availability([], [], _graph(node), now=NOW)
    assert opp is not None
    assert opp.coaching_type == CoachingType.SUPPORT_NETWORK_NUDGE.value


# ── Gate 2: timing (§6.4) ────────────────────────────────────────────────────
def _opp(coaching_type=CoachingType.PATTERN_REFLECTION.value, delivery="as_question", urgency="low"):
    from backend.layer5_relationship.schemas import CoachingOpportunity
    return CoachingOpportunity(opportunity_detected=True, coaching_type=coaching_type,
                               delivery_mode=delivery, urgency=urgency)


def _timing(**kw):
    base = dict(opportunity=_opp(), conversation_mode="social_coaching",
                primary_emotion=_emotion(), background_state=BackgroundEmotionalState(),
                relationship_stage="developing", circadian_band="afternoon")
    base.update(kw)
    return cd.gate_2_timing(**base)


def test_gate2_blocks_crisis_mode():
    assert _timing(conversation_mode="crisis") is False


def test_gate2_blocks_high_distress():
    assert _timing(primary_emotion=_emotion(valence=-0.7)) is False


def test_gate2_blocks_new_relationship_stage():
    assert _timing(relationship_stage="new") is False


def test_gate2_blocks_late_night_low_urgency():
    assert _timing(circadian_band="late_night") is False


def test_gate2_allows_receptive_state():
    assert _timing() is True


def test_gate2_soft_block_under_negative_drift_allows_only_affirming():
    drift = BackgroundEmotionalState(bes_label=BESLabel.DETERIORATING.value)
    assert _timing(background_state=drift) is False                       # pattern reflection blocked
    assert _timing(background_state=drift,
                   opportunity=_opp(CoachingType.STRENGTH_ACKNOWLEDGMENT.value,
                                    delivery="inline")) is True           # affirming allowed


# ── Gate 3: recency (§6.4) ───────────────────────────────────────────────────
def test_gate3_allows_new_pattern():
    assert cd.gate_3_recency(_opp(), None, now=NOW) is True


def test_gate3_blocks_recently_surfaced():
    p = _pattern(has_been_surfaced=True, last_observed=NOW - timedelta(days=5))
    assert cd.gate_3_recency(_opp(), p, now=NOW) is False


def test_gate3_blocks_thrice_surfaced_unacknowledged():
    p = _pattern(has_been_surfaced=True, last_observed=NOW - timedelta(days=40),
                 surface_count=3, user_acknowledged=False)
    assert cd.gate_3_recency(_opp(), p, now=NOW) is False


# ── Full detection (§6.4) ────────────────────────────────────────────────────
def test_detect_full_pass_sets_opportunity_detected():
    opp = cd.detect_coaching_opportunity(
        active_patterns=[_pattern()], recent_events=[], social_graph=_graph(),
        conversation_mode="social_coaching", primary_emotion=_emotion(),
        background_state=BackgroundEmotionalState(), relationship_stage="established",
        circadian_band="afternoon", now=NOW)
    assert opp.opportunity_detected is True
    assert opp.coaching_type is not None


def test_detect_defers_when_timing_fails():
    opp = cd.detect_coaching_opportunity(
        active_patterns=[_pattern()], recent_events=[], social_graph=_graph(),
        conversation_mode="crisis", primary_emotion=_emotion(crisis=True),
        background_state=BackgroundEmotionalState(), relationship_stage="established",
        circadian_band="afternoon", now=NOW)
    assert opp.opportunity_detected is False
    assert opp.coaching_type is not None          # valid but deferred (queue for Layer 6)
    assert opp.delivery_mode == "deferred"


def test_pattern_reflection_framed_provisionally():
    opp = cd.gate_1_availability([_pattern()], [], _graph(), now=NOW)
    text = opp.observation_text.lower()
    assert "notice" in text or "noticed" in text
    assert "?" in opp.observation_text          # invites confirmation, not a verdict
