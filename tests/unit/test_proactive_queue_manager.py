"""Tests for SC-1 Proactive Queue Manager (architecture doc §3)."""

from datetime import datetime, timedelta

from backend.layer6_proactivity import queue_manager as qm
from backend.layer6_proactivity.schemas import (
    ItemStatus,
    ProactiveItem,
    ProactiveItemType,
)

NOW = datetime(2026, 6, 28, 12, 0, 0)


def _item(item_type=ProactiveItemType.THREAD_FOLLOW_UP.value, **kw):
    base = dict(item_type=item_type, base_priority=qm.BASE_PRIORITY_BY_TYPE[item_type],
                content_basis="User mentioned an interview on Tuesday at the new company.",
                status=ItemStatus.PENDING.value)
    base.update(kw)
    return ProactiveItem(**base)


# ── Base priority (§3.3) ─────────────────────────────────────────────────────
def test_base_priority_table():
    assert qm.BASE_PRIORITY_BY_TYPE[ProactiveItemType.WELLBEING_CHECK.value] == 0.90
    assert qm.BASE_PRIORITY_BY_TYPE[ProactiveItemType.THREAD_ANNIVERSARY.value] == 0.40


# ── Age weight (§3.3) ────────────────────────────────────────────────────────
def test_age_weight_before_window_is_half():
    w = qm.compute_age_weight(NOW, NOW + timedelta(hours=2), NOW + timedelta(days=2))
    assert w == 0.5


def test_age_weight_inside_window_peaks_at_end():
    start, end = NOW - timedelta(days=1), NOW + timedelta(days=1)
    mid = qm.compute_age_weight(NOW, start, end)          # halfway → 1.25
    assert 1.0 < mid <= 1.5
    at_end = qm.compute_age_weight(end, start, end)
    assert abs(at_end - 1.5) < 1e-9


def test_age_weight_after_window_decays_with_floor():
    start, end = NOW - timedelta(days=2), NOW - timedelta(days=1)
    w = qm.compute_age_weight(NOW + timedelta(days=10), start, end)
    assert w == 0.2                                       # floored


# ── BES weight (§3.3) ────────────────────────────────────────────────────────
def test_bes_weight_boosts_wellbeing_when_deteriorating():
    assert qm.compute_bes_weight(ProactiveItemType.WELLBEING_CHECK.value, "deteriorating") == 2.5
    assert qm.compute_bes_weight(ProactiveItemType.EMOTIONAL_CHECK_IN.value, "deteriorating") == 2.0


def test_bes_weight_default_for_unrelated_type():
    assert qm.compute_bes_weight(ProactiveItemType.GOAL_CHECK_IN.value, "stable") == 1.0
    assert qm.compute_bes_weight(ProactiveItemType.GOAL_CHECK_IN.value, "deteriorating") == 0.7


# ── Context weight (§3.3) ────────────────────────────────────────────────────
def test_context_weight_silence_break_zero_when_user_returned():
    item = _item(ProactiveItemType.SILENCE_BREAK.value)
    assert qm.compute_context_weight(item, session_gap_days=0) == 0.0


def test_context_weight_conflict_resolution_boost_after_silence():
    item = _item(ProactiveItemType.CONFLICT_RESOLUTION_CHECK.value)
    assert qm.compute_context_weight(item, session_gap_days=5) == 1.4


# ── Combined priority (§3.3) ─────────────────────────────────────────────────
def test_recompute_priority_combines_weights():
    item = _item(ProactiveItemType.WELLBEING_CHECK.value,
                 optimal_send_window=(NOW - timedelta(days=1), NOW + timedelta(days=1)))
    p = qm.recompute_priority(item, bes_trend="deteriorating", now=NOW, session_gap_days=2)
    assert item.current_priority == p
    assert p > item.base_priority      # boosted by BES + age inside window


# ── Queue lifecycle (§3.4) ───────────────────────────────────────────────────
def test_add_item_evicts_lowest_when_over_capacity():
    mgr = qm.ProactiveQueueManager()
    for i in range(10):
        it = _item(ProactiveItemType.RELATIONSHIP_CHECK_IN.value)
        it.current_priority = 0.2 + i * 0.01
        mgr.add_item(it, max_items=10)
    high = _item(ProactiveItemType.WELLBEING_CHECK.value)
    high.current_priority = 0.95
    mgr.add_item(high, max_items=10)
    assert len(mgr.items) == 10
    assert high in mgr.items
    assert min(i.current_priority for i in mgr.items) > 0.2   # the lowest got evicted


def test_expire_moves_past_expiry_items():
    mgr = qm.ProactiveQueueManager()
    expired = _item(expiry_time=NOW - timedelta(days=1))
    fresh = _item(expiry_time=NOW + timedelta(days=1))
    mgr.add_item(expired)
    mgr.add_item(fresh)
    mgr.expire(now=NOW)
    assert expired.status == ItemStatus.EXPIRED.value
    assert fresh.status == ItemStatus.PENDING.value


def test_top_candidates_sorted_by_priority():
    mgr = qm.ProactiveQueueManager()
    lo, hi = _item(), _item()
    lo.current_priority, hi.current_priority = 0.3, 0.9
    mgr.add_item(lo)
    mgr.add_item(hi)
    top = mgr.top_candidates(n=2)
    assert top[0] is hi


# ── Suppression-cascade support (§3.4 / §7.3) ────────────────────────────────
def test_adjust_type_base_priority_caps_and_floors():
    mgr = qm.ProactiveQueueManager()
    t = ProactiveItemType.RELATIONSHIP_CHECK_IN.value
    for _ in range(10):
        mgr.adjust_type_base_priority(t, +0.05, max_adjustment_total=0.15)
    assert mgr.base_priority(t) <= qm.BASE_PRIORITY_BY_TYPE[t] + 0.15 + 1e-9
    for _ in range(20):
        mgr.adjust_type_base_priority(t, -0.05, min_priority_floor=0.10)
    assert mgr.base_priority(t) >= 0.10


def test_increment_ignore_count():
    mgr = qm.ProactiveQueueManager()
    t = ProactiveItemType.GOAL_CHECK_IN.value
    mgr.increment_ignore_count(t)
    mgr.increment_ignore_count(t)
    assert mgr.get_ignore_count(t) == 2
