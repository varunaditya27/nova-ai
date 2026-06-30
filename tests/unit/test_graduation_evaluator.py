"""Tests for SC-2 Graduation Evaluator — criteria + silent handoff (architecture doc §5.4)."""

from backend.layer13_onboarding import graduation_evaluator as ge
from backend.layer13_onboarding.context_constructor import make_initial_state
from backend.layer13_onboarding.schemas import (
    CommunicationStyleProfile,
    GraduationHandoff,
    GraduationResult,
)


def _ready_state():
    s = make_initial_state("u1")
    s.cold_start_session_count = 3
    s.total_exchange_count = 20
    s.user_handle = "Sam"
    s.life_phase = "student"
    s.communication_style_profile = CommunicationStyleProfile()
    s.emotional_baseline_calibrated = True
    s.primary_topic_areas = ["work", "family"]
    return s


def test_fresh_state_does_not_graduate():
    res = ge.GraduationEvaluator().evaluate(make_initial_state("u1"))
    assert isinstance(res, GraduationResult)
    assert res.should_graduate is False
    assert len(res.criteria_failed) > 0


def test_all_criteria_met_graduates():
    res = ge.GraduationEvaluator().evaluate(_ready_state())
    assert res.should_graduate is True
    assert len(res.criteria_failed) == 0
    assert len(res.criteria_met) == 7


def test_missing_single_criterion_blocks_graduation():
    s = _ready_state()
    s.user_handle = None
    res = ge.GraduationEvaluator().evaluate(s)
    assert res.should_graduate is False
    assert any(c.name == "name_or_handle_known" for c in res.criteria_failed)


def test_nice_to_have_reported_separately():
    s = _ready_state()
    s.primary_reason = "loneliness"
    res = ge.GraduationEvaluator().evaluate(s)
    assert any(c.name == "primary_reason_known" for c in res.nice_to_have_met)


# ── Silent handoff (§5.4) ────────────────────────────────────────────────────
class _FakeEngine:
    def __init__(self):
        self.calls = []
    def deactivate_cold_start_config(self): self.calls.append("deactivate_config")
    def set_personality_drift_gate(self, v): self.calls.append(("drift_gate", v))
    def activate_proactivity_engine(self): self.calls.append("proactivity")
    def activate_longitudinal_full_mode(self): self.calls.append("longitudinal")
    def trigger_first_chapter_creation(self, state): self.calls.append("first_chapter")
    def deactivate(self): self.calls.append("deactivate")


def test_execute_graduation_runs_handoff_sequence():
    s = _ready_state()
    engine = _FakeEngine()
    handoff = ge.GraduationEvaluator().execute_graduation(s, engine)
    assert isinstance(handoff, GraduationHandoff)
    assert handoff.session_count_at_graduation == 3
    # full handoff sequence executed, ending with self-termination
    assert engine.calls[-1] == "deactivate"
    assert ("drift_gate", 1.0) in engine.calls
    assert "proactivity" in engine.calls and "longitudinal" in engine.calls


def test_execute_graduation_flips_cold_start_off():
    s = _ready_state()
    ge.GraduationEvaluator().execute_graduation(s, _FakeEngine())
    assert s.cold_start is False and s.cold_start_ends is not None
