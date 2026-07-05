"""SC-2 — Goal Store (architecture doc §4).

The persistent, structured repository for all user goals, their history, and current state.
Status transitions are governed by explicit rules (not arbitrary LLM judgment), and
relevance retrieval ranks active goals against the current message.

Deterministic. The semantic comparison in retrieval is an injected ``similarity_fn``
(token-overlap default) so the store runs offline. Persistence is owned by the Layer 2
State Updater; this module is the in-process model + query surface.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Callable, Optional

from backend.layer7_goals.schemas import Goal, GoalStatus, RelevantGoal

# Explicit status transitions (architecture doc §4.6). Keys are (status, trigger);
# ("*", trigger) is a wildcard applied to any current status.
STATUS_TRANSITIONS: dict[tuple, str] = {
    # From TENTATIVE
    ("tentative", "reaffirmed"): "active",
    ("tentative", "progress_positive"): "active",
    ("tentative", "abandoned"): "abandoned",
    ("tentative", "stale_30_days"): "archived",

    # From ACTIVE / ON_TRACK / AT_RISK
    ("active", "progress_positive"): "on_track",
    ("active", "stale_21_days"): "at_risk",
    ("active", "stale_14_days"): "at_risk",        # staleness scan (§5.6) reason
    ("on_track", "progress_positive"): "on_track",
    ("on_track", "progress_negative"): "active",
    ("on_track", "stale_14_days"): "at_risk",
    ("at_risk", "progress_positive"): "active",
    ("at_risk", "stale_30_days"): "abandoned",
    ("at_risk", "abandoned"): "abandoned",

    # Terminal / wildcard
    ("*", "completed"): "completed",
    ("*", "abandoned"): "abandoned",
    ("*", "paused"): "paused",
    ("paused", "reaffirmed"): "active",
    ("paused", "stale_90_days"): "archived",
}

# Statuses considered "active" for retrieval (architecture doc §4.5).
_RETRIEVABLE_STATUSES = {
    GoalStatus.ACTIVE.value, GoalStatus.ON_TRACK.value, GoalStatus.AT_RISK.value
}
_RELEVANCE_FLOOR = 0.25


def apply_transition(current_status: str, trigger: str) -> Optional[str]:
    """Return the new status for a (status, trigger), or None if undefined (§4.6)."""
    if (current_status, trigger) in STATUS_TRANSITIONS:
        return STATUS_TRANSITIONS[(current_status, trigger)]
    if ("*", trigger) in STATUS_TRANSITIONS:
        return STATUS_TRANSITIONS[("*", trigger)]
    return None


class GoalStore:
    """In-process goal repository with lifecycle + relevance retrieval (architecture doc §4)."""

    def __init__(self, goals: Optional[list[Goal]] = None):
        self.goals: list[Goal] = goals or []

    def add_goal(self, goal: Goal) -> None:
        self.goals.append(goal)

    def update_goal(self, goal: Goal) -> None:
        for i, g in enumerate(self.goals):
            if g.goal_id == goal.goal_id:
                self.goals[i] = goal
                return
        self.goals.append(goal)

    def get(self, goal_id: str) -> Optional[Goal]:
        return next((g for g in self.goals if g.goal_id == goal_id), None)

    def load_by_status(self, statuses: list[str]) -> list[Goal]:
        wanted = set(statuses)
        return [g for g in self.goals if g.status in wanted]

    def get_relevant_goals(
        self,
        message_text: str,
        emotional_state=None,
        similarity_fn: Optional[Callable[[str, str], float]] = None,
        max_results: int = 3,
        now: Optional[datetime] = None,
    ) -> list[RelevantGoal]:
        """Rank active goals by relevance to the current message (architecture doc §4.5)."""
        now = now or datetime.utcnow()
        sim = similarity_fn or (lambda a, b: 0.0)
        active = self.load_by_status(list(_RETRIEVABLE_STATUSES))

        scored: list[tuple[Goal, float]] = []
        for goal in active:
            semantic = sim(message_text, goal.title)
            days_since = (now - goal.last_mentioned_at).days if goal.last_mentioned_at else 9999
            recency = math.exp(-0.05 * days_since)
            status_bonus = 0.2 if goal.status == GoalStatus.AT_RISK.value else 0.0
            combined = (
                0.50 * semantic
                + 0.25 * recency
                + 0.15 * goal.momentum_score
                + 0.10 * goal.emotional_weight
                + status_bonus
            )
            scored.append((goal, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            RelevantGoal(goal=g, relevance_score=round(s, 4))
            for g, s in scored[:max_results]
            if s > _RELEVANCE_FLOOR
        ]
