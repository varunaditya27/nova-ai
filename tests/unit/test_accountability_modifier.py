"""Tests for SC-4 Accountability Response Modifier (architecture doc §6)."""

from datetime import datetime, timedelta

from backend.layer7_goals import accountability_modifier as am
from backend.layer7_goals.schemas import (
    Goal,
    GoalReferenceType,
    GoalStatus,
    ProgressSignalClassification,
    ProgressSignalType,
    RelevantGoal,
)
from backend.layer3_reasoning.schemas import EmotionClassification

NOW = datetime(2026, 6, 28)


def _rg(title="Run a marathon", status=GoalStatus.ACTIVE.value, score=0.7, momentum=0.5):
    goal = Goal(title=title, status=status, momentum_score=momentum,
                created_at=NOW - timedelta(days=60))
    return RelevantGoal(goal=goal, relevance_score=score)


def _emotion(valence=0.0):
    return EmotionClassification(valence=valence)


def _decide(goals, signal=None, valence=0.0, mode="goal_planning", stage="developing"):
    return am.decide_goal_reference(goals, signal, _emotion(valence), mode, stage)


def _sig(stype):
    return ProgressSignalClassification(signal_type=stype, confidence=0.8, evidence="...")


# ── Hard blocks (§6.3 / §6.4) ────────────────────────────────────────────────
def test_crisis_mode_never_references_goal():
    pkt = _decide([_rg()], signal=_sig(ProgressSignalType.COMPLETED.value), mode="crisis")
    assert pkt.should_reference_goal is False


def test_casual_mode_never_references_goal():
    pkt = _decide([_rg()], signal=_sig(ProgressSignalType.PROGRESS_POSITIVE.value), mode="casual")
    assert pkt.should_reference_goal is False


def test_new_relationship_never_references_goal():
    pkt = _decide([_rg()], signal=_sig(ProgressSignalType.COMPLETED.value), stage="new")
    assert pkt.should_reference_goal is False


def test_no_relevant_goals_no_reference():
    pkt = _decide([], signal=_sig(ProgressSignalType.COMPLETED.value))
    assert pkt.should_reference_goal is False


# ── Reference cases (§6.3) ───────────────────────────────────────────────────
def test_completion_is_celebrated():
    pkt = _decide([_rg()], signal=_sig(ProgressSignalType.COMPLETED.value))
    assert pkt.should_reference_goal is True
    assert pkt.reference_type == GoalReferenceType.CELEBRATE_COMPLETION.value
    assert pkt.goal_reference_position == "opening"


def test_positive_progress_acknowledged():
    pkt = _decide([_rg()], signal=_sig(ProgressSignalType.PROGRESS_POSITIVE.value))
    assert pkt.reference_type == GoalReferenceType.ACKNOWLEDGE_PROGRESS.value
    assert pkt.tone_instruction == "warm_encouraging"


def test_setback_when_distressed_is_gentle():
    pkt = _decide([_rg()], signal=_sig(ProgressSignalType.PROGRESS_NEGATIVE.value), valence=-0.7)
    assert pkt.reference_type == GoalReferenceType.ACKNOWLEDGE_SETBACK.value
    assert pkt.tone_instruction == "gentle_supportive"


def test_setback_when_calm_is_practical():
    pkt = _decide([_rg()], signal=_sig(ProgressSignalType.PROGRESS_NEGATIVE.value), valence=0.0)
    assert pkt.reference_type == GoalReferenceType.ACKNOWLEDGE_SETBACK.value
    assert pkt.tone_instruction == "supportive_practical"


def test_topic_connection_without_signal():
    pkt = _decide([_rg(status=GoalStatus.ON_TRACK.value, score=0.8, momentum=0.5)], signal=None)
    assert pkt.reference_type == GoalReferenceType.CONNECT_TOPIC.value
    assert pkt.goal_reference_position == "closing"


def test_low_relevance_no_signal_is_no_reference():
    pkt = _decide([_rg(score=0.4, momentum=0.1)], signal=None)
    assert pkt.should_reference_goal is False


# ── Single-goal rule (§6.4) ──────────────────────────────────────────────────
def test_only_top_goal_is_referenced():
    pkt = _decide([_rg("Run a marathon", score=0.9), _rg("Learn piano", score=0.8)],
                  signal=_sig(ProgressSignalType.PROGRESS_POSITIVE.value))
    assert pkt.primary_goal.title == "Run a marathon"
