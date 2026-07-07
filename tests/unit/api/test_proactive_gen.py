"""Layer-6 candidate generation: goal → proactive check-in handoff (pure, offline)."""
from datetime import datetime, timedelta, timezone

from api.proactive_gen import goal_checkin_item
from backend.layer6_proactivity.schemas import ProactiveItemType
from backend.layer7_goals.schemas import Goal

_NOW = datetime(2026, 7, 7, tzinfo=timezone.utc)


def test_goal_with_upcoming_deadline_yields_checkin():
    g = Goal(goal_id="g1", title="Run a 5K", deadline=_NOW + timedelta(days=10))
    item = goal_checkin_item(g, _NOW)
    assert item is not None
    assert item.item_type == ProactiveItemType.GOAL_CHECK_IN.value
    assert item.item_id == "goalcheck-g1"           # deterministic → idempotent across turns
    assert item.source_goal_id == "g1"


def test_goal_without_any_date_yields_none():
    assert goal_checkin_item(Goal(goal_id="g2", title="Read more"), _NOW) is None


def test_past_deadline_yields_none():
    g = Goal(goal_id="g3", title="old goal", deadline=_NOW - timedelta(days=5))
    assert goal_checkin_item(g, _NOW) is None


def test_naive_deadline_is_normalized_not_crashed():
    g = Goal(goal_id="g4", title="x", deadline=datetime(2026, 7, 20))   # naive datetime
    item = goal_checkin_item(g, _NOW)
    assert item is not None and item.item_id == "goalcheck-g4"


def test_nearest_milestone_preferred_over_farther_deadline():
    from backend.layer7_goals.schemas import Milestone
    g = Goal(goal_id="g5", title="ship", deadline=_NOW + timedelta(days=30),
             milestones=[Milestone(goal_id="g5", description="beta", target_date=_NOW + timedelta(days=5))])
    item = goal_checkin_item(g, _NOW)
    assert item is not None
    assert "beta" in item.content_basis                # nearest (milestone) wins over the deadline
