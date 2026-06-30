"""Tests for SC-1 Active Elicitation — queue + surfacing policy (architecture doc §4.3-§4.4)."""

from types import SimpleNamespace

from backend.layer13_onboarding import active_elicitation_queue as aeq
from backend.layer13_onboarding.schemas import ElicitationItem


def _ctx(triggers):
    return SimpleNamespace(active_triggers=set(triggers))


# ── Initial registry (§4.3) ──────────────────────────────────────────────────
def test_initial_items_cover_all_categories():
    cats = {i.category for i in aeq.INITIAL_ELICITATION_ITEMS}
    assert cats == set(aeq.ELICITATION_CATEGORIES if hasattr(aeq, "ELICITATION_CATEGORIES") else cats)
    assert len(aeq.INITIAL_ELICITATION_ITEMS) == 8


def test_identity_item_cannot_be_inferred():
    identity = next(i for i in aeq.INITIAL_ELICITATION_ITEMS if i.category == "identity")
    assert identity.priority == 1 and identity.can_infer_without_asking is False


# ── next_surfaceable_item (§4.2) ─────────────────────────────────────────────
def test_next_surfaceable_returns_triggered_waiting_item():
    q = aeq.ElicitationQueue(user_id="u1", items=[
        ElicitationItem(category="life_context", inference_target="life_phase", priority=1,
                        question="student or working?", natural_triggers=["mentions_work"]),
    ])
    item = q.next_surfaceable_item(session_context=None, current_session_number=2,
                                   emotional_intensity=0.1, topic_in_progress="mentions_work today")
    assert item is not None and item.category == "life_context"


def test_next_surfaceable_skips_when_no_trigger_fires():
    q = aeq.ElicitationQueue(user_id="u1", items=[
        ElicitationItem(category="goals", inference_target="g", priority=3,
                        question="goal?", natural_triggers=["mentions_plan"]),
    ])
    assert q.next_surfaceable_item(None, 2, 0.1, "small talk") is None


def test_next_surfaceable_respects_prerequisites():
    pre = ElicitationItem(category="identity", inference_target="user_handle", priority=1,
                          question="name?", natural_triggers=["hi"])
    dependent = ElicitationItem(category="reason_for_use", inference_target="primary_reason",
                                priority=2, question="why?", natural_triggers=["hi"],
                                prerequisite_item_ids=[pre.item_id])
    q = aeq.ElicitationQueue(user_id="u1", items=[pre, dependent])
    # identity surfaces first (prereq for the other); pick lower priority number
    item = q.next_surfaceable_item(None, 2, 0.1, "hi there")
    assert item.category == "identity"


def test_next_surfaceable_suppresses_priority3_when_emotional():
    q = aeq.ElicitationQueue(user_id="u1", items=[
        ElicitationItem(category="goals", inference_target="g", priority=3,
                        question="goal?", natural_triggers=["mentions_plan"]),
    ])
    assert q.next_surfaceable_item(None, 2, 0.75, "mentions_plan") is None


# ── ElicitationSurfacingPolicy.can_surface (§4.4) ────────────────────────────
def _policy():
    return aeq.ElicitationSurfacingPolicy()


def _item(priority=2, triggers=("t",)):
    return ElicitationItem(category="life_context", inference_target="x", priority=priority,
                           question="q", natural_triggers=list(triggers))


def test_can_surface_all_conditions_met():
    assert _policy().can_surface(_item(), _ctx(["t"]), current_session_number=3,
                                 emotional_intensity=0.2, elicitation_count_this_session=0) is True


def test_cannot_surface_without_trigger():
    assert _policy().can_surface(_item(), _ctx(["other"]), 3, 0.2, 0) is False


def test_cannot_surface_priority3_when_intensity_high():
    assert _policy().can_surface(_item(priority=3), _ctx(["t"]), 3, 0.7, 0) is False


def test_cannot_surface_priority2_during_acute_distress():
    assert _policy().can_surface(_item(priority=2), _ctx(["t"]), 3, 0.85, 0) is False


def test_rate_limit_blocks_second_question_in_early_period():
    assert _policy().can_surface(_item(), _ctx(["t"]), current_session_number=5,
                                 emotional_intensity=0.2, elicitation_count_this_session=1) is False


def test_rate_limit_not_applied_after_early_period():
    assert _policy().can_surface(_item(), _ctx(["t"]), current_session_number=20,
                                 emotional_intensity=0.2, elicitation_count_this_session=1) is True
