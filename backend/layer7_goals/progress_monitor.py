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
from datetime import datetime
from typing import Optional

from backend.layer7_goals.schemas import (
    Goal,
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
    "done", "finished", "completed it", "achieved", "got there", "hit my goal",
    "made it", "crossed the finish line", "officially", "finally did it",
]
ABANDONMENT_SIGNALS = [
    "giving up", "gave up", "dropping it", "not worth it", "forget it",
    "decided not to", "changed my mind about", "not doing that anymore",
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
}
_MOMENTUM_DECAY = 0.1
_MOMENTUM_WINDOW_DAYS = 30
_MOMENTUM_MAX_EVENTS = 20


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
