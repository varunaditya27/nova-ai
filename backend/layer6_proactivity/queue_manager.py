"""SC-1 — Proactive Queue Manager (architecture doc §3).

The persistent, prioritized store of every item Layer 6 might send. It aggregates
candidates from the upstream intake contracts (§9), assigns priority scores, manages
lifecycle, and presents the top candidates to SC-2 every 30 minutes.

The queue is a *priority queue* whose scores evolve over time:

    P_current = P_base × W_age × W_bes × W_context

Deterministic, no LLM. The scoring functions are pure; the manager class holds the
persistent state (items, learned base-priority adjustments, ignore counts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer6_proactivity.schemas import (
    ItemStatus,
    ProactiveItem,
    ProactiveItemType,
)

# Base priority by item type (architecture doc §3.3).
BASE_PRIORITY_BY_TYPE: dict[str, float] = {
    ProactiveItemType.THREAD_FOLLOW_UP.value: 0.80,
    ProactiveItemType.EMOTIONAL_CHECK_IN.value: 0.85,
    ProactiveItemType.WELLBEING_CHECK.value: 0.90,
    ProactiveItemType.SILENCE_BREAK.value: 0.60,
    ProactiveItemType.THREAD_EXPIRY_CHECK.value: 0.65,
    ProactiveItemType.CONFLICT_RESOLUTION_CHECK.value: 0.70,
    ProactiveItemType.GOAL_CHECK_IN.value: 0.72,
    ProactiveItemType.SOCIAL_PATTERN_COACHING.value: 0.55,
    ProactiveItemType.RELATIONSHIP_CHECK_IN.value: 0.50,
    ProactiveItemType.UPCOMING_DATE_REMINDER.value: 0.78,
    ProactiveItemType.GOAL_CELEBRATION.value: 0.75,
    ProactiveItemType.POSITIVE_REINFORCEMENT.value: 0.65,
    ProactiveItemType.GOAL_ENCOURAGEMENT.value: 0.55,
    ProactiveItemType.RECURRING_CONCERN_CHECK.value: 0.45,
    ProactiveItemType.THREAD_ANNIVERSARY.value: 0.40,
    ProactiveItemType.BEHAVIORAL_PATTERN_SURFACING.value: 0.50,
    ProactiveItemType.RETROSPECTIVE_REFLECTION.value: 0.60,
}

# BES weight by 7-day trend label (architecture doc §3.3). Inner keys are item types or
# "default". Unknown trends fall back to a flat 1.0.
BES_WEIGHTS: dict[str, dict[str, float]] = {
    "positive": {
        ProactiveItemType.EMOTIONAL_CHECK_IN.value: 0.7,
        ProactiveItemType.WELLBEING_CHECK.value: 0.5,
        "default": 1.0,
    },
    "stable": {"default": 1.0},
    "mild_negative_drift": {
        ProactiveItemType.EMOTIONAL_CHECK_IN.value: 1.3,
        ProactiveItemType.WELLBEING_CHECK.value: 1.5,
        "default": 1.0,
    },
    "significant_negative_drift": {
        ProactiveItemType.EMOTIONAL_CHECK_IN.value: 1.6,
        ProactiveItemType.WELLBEING_CHECK.value: 2.0,
        "default": 0.9,
    },
    "deteriorating": {
        ProactiveItemType.EMOTIONAL_CHECK_IN.value: 2.0,
        ProactiveItemType.WELLBEING_CHECK.value: 2.5,
        "default": 0.7,
    },
}

_AGE_DECAY_WINDOW_SECONDS = 86400 * 3   # priority decays over 3 days past the window


def compute_age_weight(now: datetime, window_start: datetime, window_end: datetime) -> float:
    """Priority rises into the optimal window, peaks at its end, then decays (§3.3)."""
    if now < window_start:
        return 0.5
    if now <= window_end:
        span = (window_end - window_start).total_seconds()
        if span <= 0:
            return 1.5
        frac = (now - window_start).total_seconds() / span
        return min(1.5, 1.0 + frac * 0.5)
    overshoot = (now - window_end).total_seconds()
    return max(0.2, 1.0 - overshoot / _AGE_DECAY_WINDOW_SECONDS * 0.8)


def compute_bes_weight(item_type: str, bes_trend: str) -> float:
    """Boost wellbeing/emotional items when the user is struggling (architecture doc §3.3)."""
    trend_weights = BES_WEIGHTS.get(bes_trend)
    if not trend_weights:
        return 1.0
    return trend_weights.get(item_type, trend_weights.get("default", 1.0))


def compute_context_weight(item: ProactiveItem, session_gap_days: float) -> float:
    """Situational relevance boost/kill (architecture doc §3.3).

    A SILENCE_BREAK is irrelevant once the user has returned; a CONFLICT_RESOLUTION_CHECK
    becomes more relevant when an active conflict has gone quiet for days.
    """
    if item.item_type == ProactiveItemType.SILENCE_BREAK.value and session_gap_days < 1:
        return 0.0
    if item.item_type == ProactiveItemType.CONFLICT_RESOLUTION_CHECK.value and session_gap_days >= 5:
        return 1.4
    return 1.0


def recompute_priority(
    item: ProactiveItem,
    bes_trend: str,
    now: datetime,
    session_gap_days: float,
    base_priority: Optional[float] = None,
) -> float:
    """P_current = P_base × W_age × W_bes × W_context; updates the item (architecture doc §3.3)."""
    base = base_priority if base_priority is not None else item.base_priority
    if item.optimal_send_window:
        w_age = compute_age_weight(now, item.optimal_send_window[0], item.optimal_send_window[1])
    else:
        w_age = 1.0
    w_bes = compute_bes_weight(item.item_type, bes_trend)
    w_ctx = compute_context_weight(item, session_gap_days)
    item.current_priority = base * w_age * w_bes * w_ctx
    item.priority_last_updated = now
    return item.current_priority


class ProactiveQueueManager:
    """Persistent priority queue with learned base-priority adjustments (architecture doc §3)."""

    MAX_ITEMS = 10

    def __init__(self, items: Optional[list[ProactiveItem]] = None):
        self.items: list[ProactiveItem] = items or []
        self._base_overrides: dict[str, float] = {}   # item_type -> cumulative delta
        self._ignore_counts: dict[str, int] = {}

    def base_priority(self, item_type: str) -> float:
        base = BASE_PRIORITY_BY_TYPE.get(item_type, 0.5)
        # round() absorbs float drift so the floor/cap bounds hold exactly.
        return round(max(0.0, min(1.0, base + self._base_overrides.get(item_type, 0.0))), 6)

    def add_item(self, item: ProactiveItem, max_items: int = MAX_ITEMS) -> None:
        """Add an item; if over capacity, evict the lowest-priority item (§3.4)."""
        self.items.append(item)
        if len(self.items) > max_items:
            lowest = min(self.items, key=lambda i: i.current_priority)
            self.items.remove(lowest)

    def recompute_all(self, bes_trend: str, now: datetime, session_gap_days: float) -> None:
        for item in self.items:
            if item.status in (ItemStatus.PENDING.value, ItemStatus.DEFERRED.value):
                recompute_priority(item, bes_trend, now, session_gap_days,
                                   base_priority=self.base_priority(item.item_type))

    def expire(self, now: datetime) -> list[ProactiveItem]:
        """Mark past-expiry items expired (archived, not deleted) (§3.4)."""
        expired = []
        for item in self.items:
            if item.expiry_time and now > item.expiry_time and item.status in (
                ItemStatus.PENDING.value, ItemStatus.DEFERRED.value
            ):
                item.status = ItemStatus.EXPIRED.value
                expired.append(item)
        return expired

    def top_candidates(self, n: int = 5) -> list[ProactiveItem]:
        active = [i for i in self.items
                  if i.status in (ItemStatus.PENDING.value, ItemStatus.DEFERRED.value)]
        return sorted(active, key=lambda i: i.current_priority, reverse=True)[:n]

    def adjust_type_base_priority(
        self, item_type: str, adjustment: float,
        max_adjustment_total: float = 0.15, min_priority_floor: float = 0.10,
    ) -> None:
        """Learn from responses: nudge a type's base priority within bounds (§7.3)."""
        current = self._base_overrides.get(item_type, 0.0) + adjustment
        current = min(current, max_adjustment_total)
        base = BASE_PRIORITY_BY_TYPE.get(item_type, 0.5)
        if base + current < min_priority_floor:
            current = min_priority_floor - base
        self._base_overrides[item_type] = current

    def increment_ignore_count(self, item_type: str) -> None:
        self._ignore_counts[item_type] = self._ignore_counts.get(item_type, 0) + 1

    def get_ignore_count(self, item_type: str) -> int:
        return self._ignore_counts.get(item_type, 0)

    def reset_ignore_count(self, item_type: str) -> None:
        self._ignore_counts[item_type] = 0
