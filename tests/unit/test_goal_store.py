"""Tests for SC-2 Goal Store (architecture doc §4)."""

from datetime import datetime, timedelta

from backend.layer7_goals import goal_store as gs
from backend.layer7_goals.schemas import Goal, GoalStatus

NOW = datetime(2026, 6, 28)


def _goal(title, status=GoalStatus.ACTIVE.value, days_ago=1, momentum=0.5,
          emotional_weight=0.5, goal_id=None):
    return Goal(goal_id=goal_id or title, title=title, status=status,
                last_mentioned_at=NOW - timedelta(days=days_ago),
                momentum_score=momentum, emotional_weight=emotional_weight)


# ── Status transitions (§4.6) ────────────────────────────────────────────────
def test_transition_tentative_reaffirmed_to_active():
    assert gs.apply_transition(GoalStatus.TENTATIVE.value, "reaffirmed") == GoalStatus.ACTIVE.value


def test_transition_wildcard_completed():
    assert gs.apply_transition(GoalStatus.ON_TRACK.value, "completed") == GoalStatus.COMPLETED.value
    assert gs.apply_transition(GoalStatus.AT_RISK.value, "completed") == GoalStatus.COMPLETED.value


def test_transition_stale_moves_to_at_risk():
    assert gs.apply_transition(GoalStatus.ON_TRACK.value, "stale_14_days") == GoalStatus.AT_RISK.value


def test_transition_invalid_returns_none():
    assert gs.apply_transition(GoalStatus.COMPLETED.value, "reaffirmed") is None


# ── Retrieval (§4.5) ─────────────────────────────────────────────────────────
def test_load_by_status_filters():
    store = gs.GoalStore([_goal("a", GoalStatus.ACTIVE.value),
                          _goal("b", GoalStatus.ABANDONED.value)])
    loaded = store.load_by_status([GoalStatus.ACTIVE.value])
    assert [g.title for g in loaded] == ["a"]


def test_get_relevant_goals_ranks_by_relevance():
    store = gs.GoalStore([
        _goal("learn spanish", goal_id="g1"),
        _goal("save money", goal_id="g2"),
    ])

    def sim(msg, title):
        return 0.9 if "spanish" in title else 0.1

    res = store.get_relevant_goals("I practiced spanish today", similarity_fn=sim, now=NOW)
    assert res[0].goal.goal_id == "g1"
    assert res[0].relevance_score > 0.25


def test_get_relevant_goals_at_risk_bonus():
    store = gs.GoalStore([
        _goal("fitness", status=GoalStatus.ACTIVE.value, goal_id="g1"),
        _goal("fitness routine", status=GoalStatus.AT_RISK.value, goal_id="g2"),
    ])
    # Equal semantic similarity → the at-risk goal wins via the status bonus.
    res = store.get_relevant_goals("fitness", similarity_fn=lambda m, t: 0.5, now=NOW)
    assert res[0].goal.goal_id == "g2"


def test_get_relevant_goals_filters_below_threshold():
    store = gs.GoalStore([_goal("unrelated goal", momentum=0.0, emotional_weight=0.0,
                                days_ago=200)])
    res = store.get_relevant_goals("something else", similarity_fn=lambda m, t: 0.0, now=NOW)
    assert res == []
