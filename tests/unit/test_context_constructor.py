"""Tests for SC-2 Cold Start Handling — initial state, context builder, first message (§5)."""

from backend.layer13_onboarding import context_constructor as cc
from backend.layer13_onboarding.schemas import (
    CommunicationStyleProfile,
    InitialState,
    PersonalityVector,
)


# ── Initial state (§5.1) ─────────────────────────────────────────────────────
def test_make_initial_state_population_defaults():
    s = cc.make_initial_state("u1")
    assert isinstance(s, InitialState)
    assert s.cold_start is True and s.cold_start_session_count == 0
    assert s.personality_vector.warmth == 0.75
    assert s.emotional_baseline.engagement_level == 0.60


def test_each_user_gets_independent_state():
    a, b = cc.make_initial_state("a"), cc.make_initial_state("b")
    a.primary_topic_areas.append("work")
    assert b.primary_topic_areas == []                 # no shared mutable defaults


# ── First message (§5.2) ─────────────────────────────────────────────────────
def test_first_message_standard():
    msg = cc.generate_first_message(time_of_day="afternoon")
    assert "Nova" in msg and msg.strip().endswith("?")


def test_first_message_late_night_variant():
    assert "late" in cc.generate_first_message(time_of_day="late_night").lower()


def test_first_message_fallback_on_failure():
    # If template construction raises, fall back to the minimal hard-coded opener (§9).
    assert cc.generate_first_message(time_of_day=None) == "Hey. What's on your mind?"


# ── Context builder (§5.3) ───────────────────────────────────────────────────
def _builder():
    return cc.ColdStartContextBuilder()


def test_captures_user_handle_from_introduction():
    state = cc.make_initial_state("u1")
    upd = _builder().process_message("hi, I'm Sam", message_index=0, session_number=1,
                                     timestamp=None, initial_state=state, session_history=[])
    assert upd.updates.get("user_handle") == "Sam"


def test_life_phase_only_set_above_confidence_threshold():
    state = cc.make_initial_state("u1")
    # single weak signal (confidence 0.3) must NOT set life_phase
    weak = _builder().process_message("had a class", 0, 1, None, state, [])
    assert "life_phase" not in weak.updates
    # strong signal (multiple markers → confidence > 0.5) sets it + seeds a semantic fact
    strong = _builder().process_message("exam, assignment, campus, professor", 0, 1, None, state, [])
    assert strong.updates.get("life_phase") == "student"
    assert len(strong.updates.get("new_semantic_facts", [])) == 1


def test_comm_profile_builds_after_three_messages():
    state = cc.make_initial_state("u1")
    upd = _builder().process_message("yeah ok cool", message_index=3, session_number=1,
                                     timestamp=None, initial_state=state, session_history=[])
    prof = upd.updates.get("communication_style_profile")
    assert isinstance(prof, CommunicationStyleProfile)


def test_personality_drift_is_gated_by_cold_start_multiplier():
    state = cc.make_initial_state("u1")
    state.personality_vector = PersonalityVector(verbosity=0.45)
    # a verbose user should nudge verbosity up, but only a small gated step
    long_msg = "word " * 80
    upd = _builder().process_message(long_msg, message_index=4, session_number=1,
                                     timestamp=None, initial_state=state, session_history=[])
    drift = upd.updates.get("personality_vector_drift", {})
    assert "verbosity" in drift
    assert 0.45 < drift["verbosity"] < 0.50            # gated: tiny step, not a jump


def test_named_relationships_deduped():
    state = cc.make_initial_state("u1")
    upd = _builder().process_message("my friend Arjun called", 0, 1, None, state, [])
    assert [p.name for p in upd.updates.get("new_named_relationships", [])] == ["Arjun"]
    # apply, then re-process — Arjun should not be added twice
    state.apply_update(upd)
    upd2 = _builder().process_message("my friend Arjun called again", 1, 1, None, state, [])
    assert upd2.updates.get("new_named_relationships", []) == []
