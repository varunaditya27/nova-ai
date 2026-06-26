"""Tests for Layer 1 SC-1 pending-thread surfacing (architecture doc §3.5).

The Temporal Resolver queries the ThreadStore at session start for due narrative threads.
At most two are surfaced, ordered by composite priority (emotional_weight × tier).
"""

from datetime import datetime, timedelta
from uuid import uuid4

from backend.layer1_input import thread_tracker as tt
from backend.layer1_input.schemas import (
    ImportanceTier,
    NarrativeThread,
    ThreadStatus,
    ThreadType,
)

NOW = datetime(2026, 6, 26, 12, 0, 0)


def _thread(**overrides):
    base = dict(
        thread_id=uuid4(),
        summary="thread",
        created_at=NOW - timedelta(days=5),
        follow_up_due_at=NOW - timedelta(hours=1),  # due by default
        status=ThreadStatus.UNRESOLVED,
        emotional_weight=0.5,
        importance_tier=ImportanceTier.MEDIUM,
        thread_type=ThreadType.FUTURE_EVENT,
    )
    base.update(overrides)
    return NarrativeThread(**base)


def test_importance_tier_score_ordering():
    assert tt.importance_tier_score(ImportanceTier.CRITICAL) == 1.0
    assert tt.importance_tier_score(ImportanceTier.HIGH) == 0.75
    assert tt.importance_tier_score(ImportanceTier.MEDIUM) == 0.50
    assert tt.importance_tier_score(ImportanceTier.LOW) == 0.25


def test_priority_score_combines_weight_and_tier():
    thread = _thread(emotional_weight=0.8, importance_tier=ImportanceTier.HIGH)
    assert tt.priority_score(thread) == 0.8 * 0.75


def test_store_get_all_filters_by_status():
    store = tt.InMemoryThreadStore()
    a = _thread(status=ThreadStatus.UNRESOLVED)
    b = _thread(status=ThreadStatus.RESOLVED)
    store.add(a)
    store.add(b)
    unresolved = store.get_all(status=ThreadStatus.UNRESOLVED)
    assert a in unresolved and b not in unresolved
    assert len(store.get_all()) == 2


def test_due_candidates_excludes_future_and_resolved_and_snoozed():
    store = tt.InMemoryThreadStore()
    due = _thread()
    future = _thread(follow_up_due_at=NOW + timedelta(days=1))
    resolved = _thread(status=ThreadStatus.RESOLVED)
    snoozed = _thread(snooze_until=NOW + timedelta(days=1))
    for t in (due, future, resolved, snoozed):
        store.add(t)
    candidates = tt.due_candidates(store, NOW)
    assert candidates == [due]


def test_expired_snooze_does_not_exclude_thread():
    store = tt.InMemoryThreadStore()
    t = _thread(snooze_until=NOW - timedelta(hours=2))  # snooze already elapsed
    store.add(t)
    assert tt.due_candidates(store, NOW) == [t]


def test_due_candidates_sorted_by_priority_descending():
    store = tt.InMemoryThreadStore()
    low = _thread(emotional_weight=0.2, importance_tier=ImportanceTier.LOW)
    high = _thread(emotional_weight=0.9, importance_tier=ImportanceTier.CRITICAL)
    mid = _thread(emotional_weight=0.5, importance_tier=ImportanceTier.MEDIUM)
    for t in (low, high, mid):
        store.add(t)
    assert tt.due_candidates(store, NOW) == [high, mid, low]


def test_get_due_threads_caps_at_two():
    store = tt.InMemoryThreadStore()
    threads = [
        _thread(emotional_weight=w, importance_tier=ImportanceTier.HIGH)
        for w in (0.9, 0.8, 0.7, 0.6)
    ]
    for t in threads:
        store.add(t)
    surfaced = tt.get_due_threads(store, NOW)
    assert len(surfaced) == 2
    assert surfaced == [threads[0], threads[1]]


def test_overdue_count_is_candidates_beyond_surfaced():
    store = tt.InMemoryThreadStore()
    for w in (0.9, 0.8, 0.7, 0.6):
        store.add(_thread(emotional_weight=w))
    candidates = tt.due_candidates(store, NOW)
    surfaced = tt.get_due_threads(store, NOW)
    assert len(candidates) - len(surfaced) == 2


def test_empty_store_returns_no_threads():
    store = tt.InMemoryThreadStore()
    assert tt.get_due_threads(store, NOW) == []
    assert tt.due_candidates(store, NOW) == []
