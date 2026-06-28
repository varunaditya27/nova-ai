"""Tests for SC-5 Goal Decomposer (architecture doc §7)."""

from datetime import datetime, timedelta

from backend.layer7_goals import goal_decomposer as gd
from backend.layer7_goals.schemas import (
    Goal,
    Milestone,
    MilestoneStatus,
    ProgressSignalClassification,
    ProgressSignalType,
)
from backend.layer6_proactivity.schemas import ProactiveItemType

NOW = datetime(2026, 6, 28)


# ── Decomposition (§7.3) ─────────────────────────────────────────────────────
def test_decompose_parses_milestones_and_habits():
    def llm(prompt):
        return {
            "milestones": [
                {"title": "First 5K run", "description": "Complete a 5K", "target_date": None,
                 "progress_weight": 0.5, "confidence": 0.8},
                {"title": "10K run", "description": "Complete a 10K", "target_date": None,
                 "progress_weight": 0.5, "confidence": 0.7},
            ],
            "habits": [
                {"title": "Run 3x/week", "description": "Short runs", "frequency": "weekly",
                 "target_count_per_period": 3, "rationale": "builds endurance"},
            ],
        }

    goal = Goal(goal_id="g1", title="Run a marathon")
    milestones, habits = gd.decompose_goal(goal, llm_fn=llm, now=NOW)
    assert len(milestones) == 2
    assert milestones[0].title == "First 5K run"
    assert milestones[0].goal_id == "g1"
    assert len(habits) == 1
    assert habits[0].target_count_per_period == 3


def test_decompose_no_llm_returns_empty():
    milestones, habits = gd.decompose_goal(Goal(title="x"), now=NOW)
    assert milestones == [] and habits == []


# ── Layer 6 handoff (§7.4) ───────────────────────────────────────────────────
def test_register_milestones_creates_layer6_items_for_near_term():
    goal = Goal(goal_id="g1", title="Run a marathon", milestones=[
        Milestone(goal_id="g1", title="First 5K", description="run 5k",
                  target_date=NOW + timedelta(days=10)),
    ])
    items = gd.register_milestones_with_layer6(goal, now=NOW)
    assert len(items) == 1
    assert items[0].item_type == ProactiveItemType.GOAL_CHECK_IN.value
    assert items[0].source_goal_id == "g1"


def test_register_skips_undated_and_far_milestones():
    goal = Goal(goal_id="g1", title="g", milestones=[
        Milestone(goal_id="g1", title="no date", target_date=None),
        Milestone(goal_id="g1", title="far off", target_date=NOW + timedelta(days=200)),
        Milestone(goal_id="g1", title="past", target_date=NOW - timedelta(days=5)),
    ])
    assert gd.register_milestones_with_layer6(goal, now=NOW) == []


# ── Milestone completion detection (§7.5) ────────────────────────────────────
def test_check_milestone_completion_matches_on_positive_signal():
    goal = Goal(goal_id="g1", title="Run a marathon", milestones=[
        Milestone(goal_id="g1", title="First 5K run", description="complete a 5k",
                  status=MilestoneStatus.PENDING.value),
    ])
    sig = ProgressSignalClassification(signal_type=ProgressSignalType.PROGRESS_POSITIVE.value,
                                       confidence=0.8)
    m = gd.check_milestone_completion(goal, "I just finished my first 5K run!", sig,
                                      similarity_fn=lambda a, b: 0.9)
    assert m is not None and m.title == "First 5K run"


def test_check_milestone_completion_none_on_low_similarity():
    goal = Goal(goal_id="g1", milestones=[
        Milestone(goal_id="g1", title="First 5K run", status=MilestoneStatus.PENDING.value)])
    sig = ProgressSignalClassification(signal_type=ProgressSignalType.PROGRESS_POSITIVE.value,
                                       confidence=0.8)
    assert gd.check_milestone_completion(goal, "unrelated", sig,
                                         similarity_fn=lambda a, b: 0.1) is None
