"""SC-3 — Progress Monitor (architecture doc §5).

Continuously infers how a goal is progressing from natural language — the user never has
to give structured updates. Two modes: fast synchronous keyword inference (per message)
and asynchronous deep inference (LLM, post-session). This module implements the
deterministic surface: signal classification, the progress-score update formula, the
momentum metric, and the 24-hour staleness scan.

Deterministic; no LLM on the inline path. The post-session deep inference (§5.5) is an
LLM call wired by the pipeline (its prompt lives in the doc) and is intentionally out of
the synchronous path that this module guarantees never blocks a response (§10).
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Callable, Optional

from backend.layer7_goals.schemas import (
    Goal,
    GoalSignalEvent,
    Habit,
    HabitFrequency,
    GoalSignalEventType,
    GoalStateChange,
    GoalStatus,
    ProgressSignalClassification,
    ProgressSignalType,
)

# Inline signal keyword sets (architecture doc §5.2).
POSITIVE_PROGRESS_SIGNALS = [
    "did it", "completed", "finished", "made it", "went ahead", "actually did",
    "kept at it", "stuck to it", "back on track", "good week", "progress",
    "getting better", "improving", "feels easier", "didn't skip", "hit my",
    "hit a milestone", "streak", "consecutive", "getting closer",
]
NEGATIVE_PROGRESS_SIGNALS = [
    "slipped up", "messed up", "haven't", "failed to", "gave up on",
    "not doing it", "stopped", "quit", "too hard", "can't keep up",
    "fell off", "derailed", "skipped", "missed", "behind on",
    "haven't touched it", "totally forgot", "been avoiding",
]
COMPLETION_SIGNALS = [
    "completed it", "achieved", "got there", "hit my goal",
    "crossed the finish line", "finally did it", "i did it", "reached my goal", "finished it",
    "i finished", "i completed",
]
ABANDONMENT_SIGNALS = [
    "giving up on", "gave up on", "dropping it", "decided not to", "changed my mind about",
    "not doing that anymore",
    "not realistic", "not the right time",
]

# Progress deltas by signal type (architecture doc §5.3).
PROGRESS_DELTAS = {
    ProgressSignalType.PROGRESS_POSITIVE.value: +0.10,
    ProgressSignalType.PROGRESS_NEGATIVE.value: -0.08,
    "milestone_reached": +0.20,
    "milestone_missed": -0.05,
    "habit_checked": +0.03,
    "reaffirmed": +0.01,
    "obstacle_mentioned": -0.02,
}

# Momentum signal weights (architecture doc §5.4).
_MOMENTUM_WEIGHTS = {
    GoalSignalEventType.PROGRESS_POSITIVE.value: 1.0,
    GoalSignalEventType.PROGRESS_NEGATIVE.value: 0.5,
    GoalSignalEventType.REAFFIRMED.value: 0.3,
    GoalSignalEventType.HABIT_CHECKED.value: 1.0,
}
_MOMENTUM_DECAY = 0.1
_MOMENTUM_WINDOW_DAYS = 30
_MOMENTUM_MAX_EVENTS = 20


# A signal only counts for a goal the message is actually *about*. Goal relevance is mostly
# query-independent (recency, momentum, emotional weight), so without this gate "I'm done for the
# day" completed whichever goal was mentioned most recently.
_MIN_GOAL_SEMANTIC = 0.5


def classify_signal_for_goal(
    message: str, goal: Goal, similarity_fn: Optional[Callable[[str, str], float]] = None
) -> Optional[ProgressSignalClassification]:
    from backend.layer7_goals.goal_extractor import _token_overlap
    if (similarity_fn or _token_overlap)(message, goal.title) < _MIN_GOAL_SEMANTIC:
        return None
    return classify_progress_signal(message, goal)


def classify_progress_signal(
    message: str, goal: Optional[Goal] = None
) -> Optional[ProgressSignalClassification]:
    """Detect the polarity of a progress signal in a message (architecture doc §5.2)."""
    low = (message or "").lower()

    for sig in COMPLETION_SIGNALS:
        if sig in low:
            return ProgressSignalClassification(
                signal_type=ProgressSignalType.COMPLETED.value, confidence=0.85, evidence=message)
    for sig in ABANDONMENT_SIGNALS:
        if sig in low:
            return ProgressSignalClassification(
                signal_type=ProgressSignalType.ABANDONED.value, confidence=0.80, evidence=message)

    positive = sum(1 for s in POSITIVE_PROGRESS_SIGNALS if s in low)
    negative = sum(1 for s in NEGATIVE_PROGRESS_SIGNALS if s in low)
    if positive > 0 and positive > negative:
        return ProgressSignalClassification(
            signal_type=ProgressSignalType.PROGRESS_POSITIVE.value,
            confidence=min(0.5 + 0.1 * positive, 0.90), evidence=message)
    if negative > 0 and negative > positive:
        return ProgressSignalClassification(
            signal_type=ProgressSignalType.PROGRESS_NEGATIVE.value,
            confidence=min(0.5 + 0.1 * negative, 0.90), evidence=message)
    return None


def update_progress_score(goal: Goal, signal: ProgressSignalClassification) -> float:
    """Apply ``P_new = P_old + ΔP × confidence`` and clamp to [0, 1] (architecture doc §5.3)."""
    if signal.signal_type == ProgressSignalType.COMPLETED.value:
        goal.progress_score = 1.0
        return goal.progress_score
    if signal.signal_type == ProgressSignalType.ABANDONED.value:
        return goal.progress_score   # unchanged; status handled by the transition rules

    delta = PROGRESS_DELTAS.get(signal.signal_type, 0.0)
    goal.progress_score = max(0.0, min(1.0, goal.progress_score + delta * signal.confidence))
    return goal.progress_score


# First-person past-tense statements of having *done* the thing ("I went for a run this morning")
# — a habit check-in that the generic progress keywords ("did it", "stuck to it") would miss.
_DID_THE_THING = re.compile(
    r"\b(i|we)\s+(just |finally |also |actually )?(went|did|ran|walked|worked out|practi[sc]ed|"
    r"studied|read|wrote|meditated|stretched|cooked|trained|completed|finished|stuck|kept)\b",
    re.IGNORECASE)
_MIN_HABIT_SEMANTIC = 0.5


def _period(when: datetime, frequency: str) -> int:
    """Day index, or Monday-aligned week index for weekly habits — consecutive periods differ by 1."""
    day = when.date().toordinal()
    return (day - 1) // 7 if frequency == HabitFrequency.WEEKLY.value else day


def record_habit_check_in(
    goal: Goal, message: str, similarity_fn: Callable[[str, str], float], now: datetime
) -> Optional[Habit]:
    """Count the message as a check-in on the goal's best-matching active habit (§7 SC-5).

    Idempotent per period (two runs in one day are one daily check-in); a missed period resets
    the streak to 1. Returns the updated habit, or None when nothing was checked in.
    """
    positive = classify_progress_signal(message, goal)
    done = _DID_THE_THING.search(message or "") or (
        positive is not None and positive.signal_type in (
            ProgressSignalType.PROGRESS_POSITIVE.value, ProgressSignalType.COMPLETED.value))
    if not done:
        return None
    scored = [(similarity_fn(message, f"{h.title} {h.description}".strip()), h)
              for h in goal.habits if h.status == "active"]
    if not scored:
        return None
    best_score, habit = max(scored, key=lambda t: t[0])
    if best_score < _MIN_HABIT_SEMANTIC:
        return None
    period = _period(now, habit.frequency)
    last = None if habit.last_checked_in is None else _period(habit.last_checked_in, habit.frequency)
    if last == period:
        return None
    habit.current_streak = habit.current_streak + 1 if last == period - 1 else 1
    habit.best_streak = max(habit.best_streak, habit.current_streak)
    habit.total_check_ins += 1
    habit.last_checked_in = now
    goal.progress_score = min(1.0, goal.progress_score + PROGRESS_DELTAS["habit_checked"])
    goal.signal_events.append(GoalSignalEvent(
        goal_id=goal.goal_id, event_type=GoalSignalEventType.HABIT_CHECKED.value,
        timestamp=now, evidence_text=message, confidence=best_score))
    goal.momentum_score = compute_momentum(goal.signal_events, now=now)
    goal.last_mentioned_at = now
    return habit


def compute_momentum(signal_events: list, now: Optional[datetime] = None) -> float:
    """Recency/frequency-weighted engagement in [0, 1] (architecture doc §5.4)."""
    now = now or datetime.utcnow()
    recent = [
        e for e in signal_events
        if e.timestamp and (now - e.timestamp).days <= _MOMENTUM_WINDOW_DAYS
    ]
    recent.sort(key=lambda e: e.timestamp, reverse=True)
    recent = recent[:_MOMENTUM_MAX_EVENTS]
    if not recent:
        return 0.0
    total = 0.0
    for e in recent:
        d = (now - e.timestamp).days
        w = _MOMENTUM_WEIGHTS.get(e.event_type, 0.5)
        total += math.exp(-_MOMENTUM_DECAY * d) * w
    return round(min(1.0, total / len(recent)), 4)


def run_staleness_scan(goals: list[Goal], now: Optional[datetime] = None) -> list[GoalStateChange]:
    """Apply staleness transitions to active goals (architecture doc §5.6)."""
    now = now or datetime.utcnow()
    changes: list[GoalStateChange] = []
    for goal in goals:
        if not goal.last_mentioned_at:
            continue
        days_since = (now - goal.last_mentioned_at).days
        if goal.status == GoalStatus.TENTATIVE.value and days_since >= 30:
            changes.append(GoalStateChange(goal.goal_id, GoalStatus.ARCHIVED.value, "stale_30_days"))
        elif goal.status in (GoalStatus.ACTIVE.value, GoalStatus.ON_TRACK.value) and days_since >= 14:
            changes.append(GoalStateChange(goal.goal_id, GoalStatus.AT_RISK.value, "stale_14_days"))
        elif goal.status == GoalStatus.AT_RISK.value and days_since >= 30:
            changes.append(GoalStateChange(goal.goal_id, GoalStatus.ABANDONED.value, "stale_30_days"))
    return changes
