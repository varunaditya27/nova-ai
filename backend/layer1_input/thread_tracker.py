"""Layer 1 · Pending-thread surfacing (architecture doc §3.5).

Narrative threads — open loops from previous conversations — live in a ``ThreadStore``.
At session start the Temporal Resolver asks which are *due*. At most two are surfaced per
session, ordered by composite priority (``emotional_weight × importance_tier``).

The thread *records* are created and resolved by the Layer 2 State Updater after each turn;
Layer 1 is a read-only consumer. ``ThreadStore`` is a Protocol so a production SQLite-backed
store (``threads.db``, §8) can be swapped in for ``InMemoryThreadStore`` without code change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from .schemas import ImportanceTier, NarrativeThread, ThreadStatus

# Maximum threads surfaced per session (§3.5).
MAX_SURFACED_THREADS = 2

_TIER_SCORE: dict[ImportanceTier, float] = {
    ImportanceTier.CRITICAL: 1.0,
    ImportanceTier.HIGH: 0.75,
    ImportanceTier.MEDIUM: 0.50,
    ImportanceTier.LOW: 0.25,
}


class ThreadStore(Protocol):
    """Read interface Layer 1 needs from any narrative-thread store."""

    def get_all(self, status: Optional[ThreadStatus] = None) -> list[NarrativeThread]: ...


class InMemoryThreadStore:
    """Default in-process ThreadStore (used in tests and before a DB store is wired)."""

    def __init__(self, threads: Optional[list[NarrativeThread]] = None) -> None:
        self._threads: list[NarrativeThread] = list(threads) if threads else []

    def add(self, thread: NarrativeThread) -> None:
        self._threads.append(thread)

    def get_all(self, status: Optional[ThreadStatus] = None) -> list[NarrativeThread]:
        if status is None:
            return list(self._threads)
        return [t for t in self._threads if t.status == status]


def importance_tier_score(tier: ImportanceTier) -> float:
    """Numeric weight for an importance tier (§3.5 priority composition)."""
    return _TIER_SCORE[tier]


def priority_score(thread: NarrativeThread) -> float:
    """Composite surfacing priority: emotional weight scaled by importance tier (§3.5)."""
    return thread.emotional_weight * importance_tier_score(thread.importance_tier)


def _is_due(thread: NarrativeThread, now: datetime) -> bool:
    return (
        thread.follow_up_due_at <= now
        and (thread.snooze_until is None or thread.snooze_until <= now)
    )


def due_candidates(store: ThreadStore, now: datetime) -> list[NarrativeThread]:
    """All unresolved threads past their follow-up time, sorted by priority desc (§3.5)."""
    candidates = [t for t in store.get_all(status=ThreadStatus.UNRESOLVED) if _is_due(t, now)]
    return sorted(candidates, key=priority_score, reverse=True)


def get_due_threads(
    store: ThreadStore, now: datetime, max_threads: int = MAX_SURFACED_THREADS
) -> list[NarrativeThread]:
    """Top-priority due threads to surface this session — at most ``max_threads`` (§3.5)."""
    return due_candidates(store, now)[:max_threads]
