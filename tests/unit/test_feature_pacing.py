"""Tests for SC-3 Feature Introduction Pacing — registry + controller (architecture doc §6)."""

from types import SimpleNamespace

from backend.layer13_onboarding import feature_pacing as fp
from backend.layer13_onboarding.context_constructor import make_initial_state
from backend.layer13_onboarding.schemas import FeatureIntroductionEvent, IntroductionStyle


def _ctx(shared=True, pos=10, surprises=False, returns=10):
    return SimpleNamespace(
        user_has_shared_personally=shared,
        positive_engagement_session_count=pos,
        negative_surprise_events_detected=surprises,
        voluntary_return_count=returns,
    )


# ── Registry (§6.3) ──────────────────────────────────────────────────────────
def test_registry_has_safety_exception_with_zero_prereqs():
    crisis = next(p for p in fp.FEATURE_INTRODUCTION_REGISTRY
                  if p.feature_id == "crisis_resource_awareness")
    assert crisis.technical_prereqs.minimum_sessions == 0
    assert crisis.technical_prereqs.minimum_exchanges == 0


def test_registry_covers_expected_features():
    ids = {p.feature_id for p in fp.FEATURE_INTRODUCTION_REGISTRY}
    assert {"personality_adaptation", "goal_tracking", "weekly_summary",
            "retrospective", "crisis_resource_awareness"} <= ids


# ── is_feature_active (§6.4) ─────────────────────────────────────────────────
def test_crisis_always_active_even_at_session_zero():
    state = make_initial_state("u1")
    assert fp.FeaturePacingController().is_feature_active(
        "crisis_resource_awareness", state, _ctx(shared=False, pos=0, returns=0)) is True


def test_personality_adaptation_active_from_session_one():
    state = make_initial_state("u1")
    state.cold_start_session_count = 1
    state.total_exchange_count = 1
    assert fp.FeaturePacingController().is_feature_active(
        "personality_adaptation", state, _ctx(shared=False, pos=0, returns=0)) is True


def test_goal_tracking_gated_until_cold_start_complete():
    state = make_initial_state("u1")
    state.cold_start_session_count = 4
    state.total_exchange_count = 20
    state.life_phase = "student"
    state.primary_topic_areas = ["work", "study"]
    state.cold_start = True                              # not graduated yet
    assert fp.FeaturePacingController().is_feature_active(
        "goal_tracking", state, _ctx()) is False
    state.cold_start = False                             # graduated
    assert fp.FeaturePacingController().is_feature_active(
        "goal_tracking", state, _ctx()) is True


def test_missing_required_context_field_blocks_feature():
    state = make_initial_state("u1")
    state.cold_start_session_count = 4
    state.total_exchange_count = 20
    state.cold_start = False
    state.primary_topic_areas = ["work", "study"]       # life_phase still None
    assert fp.FeaturePacingController().is_feature_active(
        "goal_tracking", state, _ctx()) is False


def test_unknown_feature_is_not_blocked():
    assert fp.FeaturePacingController().is_feature_active(
        "made_up_feature", make_initial_state("u1"), _ctx()) is True


# ── queue_introduction_if_ready (§6.4) ───────────────────────────────────────
def test_queue_introduction_emits_once_then_dedupes():
    state = make_initial_state("u1")
    state.cold_start_session_count = 1
    state.total_exchange_count = 1
    ctrl = fp.FeaturePacingController()
    ev = ctrl.queue_introduction_if_ready("personality_adaptation", state, _ctx(), trigger_fired=True)
    assert isinstance(ev, FeatureIntroductionEvent)
    assert ev.introduction_style == IntroductionStyle.SILENT.value
    # second call for the same feature does not re-introduce
    assert ctrl.queue_introduction_if_ready(
        "personality_adaptation", state, _ctx(), trigger_fired=True) is None


def test_queue_introduction_requires_trigger():
    state = make_initial_state("u1")
    state.cold_start_session_count = 1
    state.total_exchange_count = 1
    assert fp.FeaturePacingController().queue_introduction_if_ready(
        "personality_adaptation", state, _ctx(), trigger_fired=False) is None
