"""SC-5 — Goal Decomposer (architecture doc §7).

Breaks a newly active goal into milestones (discrete checkpoints) and habits (recurring
supporting behaviors), and registers near-term milestones with Layer 6's proactive queue.
Runs asynchronously off the message path (triggered on transition to ``active``).

The decomposition LLM is injected as ``llm_fn`` and the milestone-completion comparison as
``similarity_fn``, so the component runs offline. The Layer 6 handoff reuses Layer 6's
intake contract (`on_goal_milestone_approaching`), closing the loop the Proactive Engine
already consumes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.layer6_proactivity.intake import on_goal_milestone_approaching
from backend.layer7_goals.schemas import (
    Goal,
    Habit,
    HabitFrequency,
    Milestone,
    MilestoneStatus,
    ProgressSignalClassification,
    ProgressSignalType,
)

_HANDOFF_HORIZON_DAYS = 90
_MILESTONE_MATCH_THRESHOLD = 0.70


def _parse_date(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def build_decomposition_prompt(goal: Goal) -> str:
    """Assemble the decomposition prompt (architecture doc §7.3)."""
    return (
        "SYSTEM:\nYou are a goal planning specialist. Break the user's personal goal into "
        "concrete milestones and supporting habits.\n\n"
        f"Goal: {goal.title}\nDescription: {goal.description}\n"
        f"Direction: {goal.direction}\nDomain: {goal.domain}\n"
        f"Deadline: {goal.deadline_description or 'open-ended'}\n"
        f"User-stated metric: {goal.metric_description or 'none stated'}\n"
        f"Obstacles noted: {goal.obstacles_noted}\nStrategies noted: {goal.strategies_noted}\n\n"
        "Generate 2-5 observable milestones (weights ~sum to 1.0) and 1-3 recurring habits. "
        "Keep language grounded in what the user said. Return JSON with 'milestones' and 'habits'."
    )


def decompose_goal(
    goal: Goal,
    llm_fn: Optional[Callable[[str], object]] = None,
    now: Optional[datetime] = None,
) -> tuple[list[Milestone], list[Habit]]:
    """Decompose a goal into milestones + habits (architecture doc §7.3).

    Returns ``([], [])`` when no ``llm_fn`` is supplied or the call fails (§10 — milestones
    are left empty and decomposition is retried after the next session).
    """
    now = now or datetime.utcnow()
    if llm_fn is None:
        return [], []
    try:
        raw = llm_fn(build_decomposition_prompt(goal))
    except Exception:
        return [], []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return [], []
    if not isinstance(raw, dict):
        return [], []

    milestones = [
        Milestone(
            goal_id=goal.goal_id,
            title=m.get("title", ""),
            description=m.get("description", ""),
            target_date=_parse_date(m.get("target_date")),
            progress_weight=float(m.get("progress_weight", 0.25)),
            created_at=now,
            created_by="system",
        )
        for m in raw.get("milestones", [])
    ]
    habits = [
        Habit(
            goal_id=goal.goal_id,
            title=h.get("title", ""),
            description=h.get("description", ""),
            frequency=h.get("frequency", HabitFrequency.WEEKLY.value),
            target_count_per_period=int(h.get("target_count_per_period", 1)),
            created_at=now,
        )
        for h in raw.get("habits", [])
    ]
    return milestones, habits


def register_milestones_with_layer6(goal: Goal, now: Optional[datetime] = None) -> list:
    """Register near-term dated milestones with Layer 6's queue (architecture doc §7.4)."""
    now = now or datetime.utcnow()
    items = []
    for milestone in goal.milestones:
        if not milestone.target_date:
            continue
        days_until = (milestone.target_date - now).days
        if 0 < days_until <= _HANDOFF_HORIZON_DAYS:
            items.append(on_goal_milestone_approaching(
                goal_id=goal.goal_id,
                goal_title=goal.title,
                milestone_description=milestone.description or milestone.title,
                due_date=milestone.target_date,
                now=now,
            ))
    return items


def check_milestone_completion(
    goal: Goal,
    user_message: str,
    progress_signal: ProgressSignalClassification,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> Optional[Milestone]:
    """Detect whether a pending milestone was just reached (architecture doc §7.5)."""
    if progress_signal.signal_type not in (
        ProgressSignalType.PROGRESS_POSITIVE.value, ProgressSignalType.COMPLETED.value
    ):
        return None
    sim = similarity_fn or (lambda a, b: 0.0)
    for milestone in goal.milestones:
        if milestone.status != MilestoneStatus.PENDING.value:
            continue
        text = f"{milestone.title} {milestone.description}".strip()
        if sim(text, user_message) > _MILESTONE_MATCH_THRESHOLD:
            return milestone
    return None
