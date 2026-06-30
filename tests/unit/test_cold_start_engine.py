"""Tests for the Cold Start Engine coordinator — lifecycle (architecture doc §7)."""

from types import SimpleNamespace

from backend.layer13_onboarding import cold_start_engine as cse
from backend.layer13_onboarding.schemas import (
    CommunicationStyleProfile,
    MessageDirectives,
    SessionEndResult,
    SessionStartDirectives,
)


def _session_ctx(**kw):
    base = dict(
        recent_history=[], emotional_intensity=0.1, current_topic="",
        active_triggers=set(), elicitation_count_this_session=0,
        feature_triggers={}, user_has_shared_personally=True,
        positive_engagement_session_count=10, negative_surprise_events_detected=False,
        voluntary_return_count=10,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _engine():
    return cse.ColdStartEngine("u1")


# ── on_session_start (§7) ────────────────────────────────────────────────────
def test_session_start_increments_count_and_returns_directives():
    eng = _engine()
    d = eng.on_session_start(_session_ctx())
    assert isinstance(d, SessionStartDirectives)
    assert eng.state.cold_start_session_count == 1
    assert d.personality_drift_gate == 0.30
    assert d.proactivity_mode == "observe_only"


def test_session_start_lists_crisis_feature_active():
    d = _engine().on_session_start(_session_ctx())
    assert "crisis_resource_awareness" in d.active_features


# ── on_message (§7) ──────────────────────────────────────────────────────────
def test_on_message_updates_state_from_passive_signals():
    eng = _engine()
    eng.on_session_start(_session_ctx())
    d = eng.on_message("hi, I'm Sam", _session_ctx(), timestamp=None)
    assert isinstance(d, MessageDirectives)
    assert eng.state.user_handle == "Sam"


def test_on_message_surfaces_one_elicitation_when_triggered():
    eng = _engine()
    eng.on_session_start(_session_ctx())
    ctx = _session_ctx(current_topic="user_mentions_work_or_job today",
                        active_triggers={"user_mentions_work_or_job"})
    d = eng.on_message("work has been a lot", ctx, timestamp=None)
    assert d.pending_elicitation_question is not None
    assert d.pending_elicitation_question.category == "life_context"


def test_on_message_collects_feature_introduction_events():
    eng = _engine()
    eng.on_session_start(_session_ctx())
    ctx = _session_ctx(feature_triggers={"personality_adaptation": True})
    d = eng.on_message("hello", ctx, timestamp=None)
    assert any(e.feature_id == "personality_adaptation" for e in d.feature_introduction_events)


# ── on_session_end (§7) ──────────────────────────────────────────────────────
def test_session_end_does_not_graduate_when_criteria_unmet():
    eng = _engine()
    eng.on_session_start(_session_ctx())
    res = eng.on_session_end(_session_ctx())
    assert isinstance(res, SessionEndResult)
    assert res.graduated is False
    assert len(res.criteria_remaining) > 0


def test_session_end_graduates_when_ready_and_self_terminates():
    eng = _engine()
    eng.state.cold_start_session_count = 3
    eng.state.total_exchange_count = 20
    eng.state.user_handle = "Sam"
    eng.state.life_phase = "student"
    eng.state.communication_style_profile = CommunicationStyleProfile()
    eng.state.emotional_baseline_calibrated = True
    eng.state.primary_topic_areas = ["work", "family"]
    res = eng.on_session_end(_session_ctx())
    assert res.graduated is True and res.handoff is not None
    assert eng.active is False and eng.state.cold_start is False
