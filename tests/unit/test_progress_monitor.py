"""Tests for SC-3 Progress Monitor (architecture doc §5)."""

from datetime import datetime, timedelta

from backend.layer7_goals import progress_monitor as pm
from backend.layer7_goals.schemas import (
    Goal,
    GoalSignalEvent,
    GoalSignalEventType,
    GoalStatus,
    ProgressSignalClassification,
    ProgressSignalType,
)

NOW = datetime(2026, 6, 28)


# ── Signal classification (§5.2) ─────────────────────────────────────────────
def test_classify_completion():
    sig = pm.classify_progress_signal("I finally did it, finished my goal!")
    assert sig.signal_type == ProgressSignalType.COMPLETED.value


def test_classify_abandonment():
    sig = pm.classify_progress_signal("honestly I'm giving up on this, not worth it")
    assert sig.signal_type == ProgressSignalType.ABANDONED.value


def test_classify_positive_progress():
    sig = pm.classify_progress_signal("good week — I stuck to it and made progress")
    assert sig.signal_type == ProgressSignalType.PROGRESS_POSITIVE.value
    assert sig.confidence > 0.5


def test_classify_negative_progress():
    sig = pm.classify_progress_signal("I slipped up and skipped it, fell off track")
    assert sig.signal_type == ProgressSignalType.PROGRESS_NEGATIVE.value


def test_classify_none_for_neutral():
    assert pm.classify_progress_signal("the weather is fine today") is None


# ── Progress score update (§5.3) ─────────────────────────────────────────────
def test_update_positive_increases_score():
    goal = Goal(progress_score=0.5)
    new = pm.update_progress_score(goal, ProgressSignalClassification(
        signal_type=ProgressSignalType.PROGRESS_POSITIVE.value, confidence=1.0))
    assert new > 0.5 and goal.progress_score == new


def test_update_negative_decreases_score():
    goal = Goal(progress_score=0.5)
    new = pm.update_progress_score(goal, ProgressSignalClassification(
        signal_type=ProgressSignalType.PROGRESS_NEGATIVE.value, confidence=1.0))
    assert new < 0.5


def test_update_completed_sets_full_score():
    goal = Goal(progress_score=0.3)
    new = pm.update_progress_score(goal, ProgressSignalClassification(
        signal_type=ProgressSignalType.COMPLETED.value, confidence=0.9))
    assert new == 1.0


def test_update_abandoned_leaves_score_unchanged():
    goal = Goal(progress_score=0.4)
    new = pm.update_progress_score(goal, ProgressSignalClassification(
        signal_type=ProgressSignalType.ABANDONED.value, confidence=0.8))
    assert new == 0.4


def test_update_clamps_to_unit_interval():
    goal = Goal(progress_score=0.97)
    new = pm.update_progress_score(goal, ProgressSignalClassification(
        signal_type=ProgressSignalType.PROGRESS_POSITIVE.value, confidence=1.0))
    assert new <= 1.0


# ── Momentum (§5.4) ──────────────────────────────────────────────────────────
def _event(event_type, days_ago):
    return GoalSignalEvent(event_type=event_type, timestamp=NOW - timedelta(days=days_ago))


def test_momentum_high_for_recent_positive_activity():
    events = [_event(GoalSignalEventType.PROGRESS_POSITIVE.value, d) for d in (0, 1, 2)]
    assert pm.compute_momentum(events, now=NOW) > 0.6


def test_momentum_zero_when_no_recent_events():
    assert pm.compute_momentum([], now=NOW) == 0.0


def test_momentum_low_for_old_events():
    events = [_event(GoalSignalEventType.PROGRESS_POSITIVE.value, d) for d in (20, 25, 28)]
    assert pm.compute_momentum(events, now=NOW) < 0.2


# ── Staleness scan (§5.6) ────────────────────────────────────────────────────
def _goal(status, days_ago, goal_id="g"):
    return Goal(goal_id=goal_id, status=status, last_mentioned_at=NOW - timedelta(days=days_ago))


def test_staleness_active_to_at_risk_after_14_days():
    changes = pm.run_staleness_scan([_goal(GoalStatus.ACTIVE.value, 15)], now=NOW)
    assert changes[0].new_status == GoalStatus.AT_RISK.value
    assert changes[0].reason == "stale_14_days"


def test_staleness_at_risk_to_abandoned_after_30_days():
    changes = pm.run_staleness_scan([_goal(GoalStatus.AT_RISK.value, 31)], now=NOW)
    assert changes[0].new_status == GoalStatus.ABANDONED.value


def test_staleness_tentative_to_archived_after_30_days():
    changes = pm.run_staleness_scan([_goal(GoalStatus.TENTATIVE.value, 31)], now=NOW)
    assert changes[0].new_status == GoalStatus.ARCHIVED.value


def test_staleness_fresh_goal_unchanged():
    assert pm.run_staleness_scan([_goal(GoalStatus.ACTIVE.value, 3)], now=NOW) == []
