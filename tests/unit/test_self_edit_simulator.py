"""Tests for SC-1 Self-Edit Simulator (architecture doc §3.4)."""

from backend.layer9_output import self_edit_simulator as se
from backend.layer9_output.schemas import SelfEditPlan


class _Rng:
    """Deterministic rng; ``r`` controls the fire/skip probability gate."""
    def __init__(self, r=0.0):
        self._r = r
    def random(self):
        return self._r
    def uniform(self, a, b):
        return (a + b) / 2
    def randint(self, a, b):
        return (a + b) // 2


DRAFT = "I think you should probably just tell them directly about how you feel."
FINAL = "Maybe it's worth gently bringing it up when the moment feels right."


def _plan(draft=DRAFT, final=FINAL, complexity=0.8, stage="friend", mode="casual_chat", r=0.0):
    return se.plan_self_edit(draft, final, complexity_score=complexity,
                             relationship_stage=stage, conversation_mode=mode, rng=_Rng(r))


def test_disabled_in_crisis_mode():
    assert _plan(mode="crisis_support") is None


def test_disabled_for_strangers():
    assert _plan(stage="stranger") is None


def test_disabled_in_task_help():
    assert _plan(mode="task_help") is None


def test_skips_when_probability_not_met():
    assert _plan(r=0.99) is None        # random() > p_self_edit → no edit


def test_fires_and_returns_plan_when_clause_changed():
    plan = _plan(r=0.0)
    assert isinstance(plan, SelfEditPlan)
    assert plan.phrase_to_show_then_delete
    assert plan.insert_after_chars >= 0
    assert plan.deletion_pause_ms > 0


def test_no_plan_when_draft_equals_final():
    assert _plan(draft=FINAL, final=FINAL, r=0.0) is None  # nothing was changed
