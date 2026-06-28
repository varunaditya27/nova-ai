"""Tests for SC-5 Response Tracker (architecture doc §7)."""

from datetime import datetime, timedelta

from backend.layer6_proactivity import response_tracker as rt
from backend.layer6_proactivity import queue_manager as qm
from backend.layer6_proactivity.schemas import (
    ItemStatus,
    ProactiveItem,
    ProactiveItemType,
    ResponseClassification,
    ResponseType,
)

SENT = datetime(2026, 6, 28, 10, 0, 0)


def _item(item_type=ProactiveItemType.GOAL_CHECK_IN.value):
    return ProactiveItem(item_type=item_type, status=ItemStatus.SENT.value)


# ── Response classification window (§7.2) ────────────────────────────────────
def test_no_messages_in_window_is_ignored():
    res = rt.classify_response(SENT, [], now=SENT + timedelta(hours=49))
    assert res.responded is False
    assert res.response_type == ResponseType.IGNORED.value
    assert res.engagement_score == 0.0


def test_immediate_response():
    msgs = [(SENT + timedelta(minutes=20), "yes it went really well, thank you!")]
    res = rt.classify_response(SENT, msgs)
    assert res.responded is True
    assert res.response_type == ResponseType.IMMEDIATE.value


def test_delayed_response():
    msgs = [(SENT + timedelta(hours=30), "sorry, been busy")]
    res = rt.classify_response(SENT, msgs)
    assert res.responded is True
    assert res.response_type == ResponseType.DELAYED.value


def test_message_outside_window_ignored():
    msgs = [(SENT + timedelta(hours=60), "hey")]
    res = rt.classify_response(SENT, msgs)
    assert res.responded is False


def test_engagement_score_in_range():
    msgs = [(SENT + timedelta(minutes=10), "yes! that went great, thanks for remembering")]
    res = rt.classify_response(SENT, msgs)
    assert 0.0 <= res.engagement_score <= 1.0
    assert res.engagement_score > 0.5      # quick + positive + substantive


# ── Feedback loop to the queue (§7.3) ────────────────────────────────────────
def test_positive_response_boosts_priority_and_confirms_preference():
    mgr = qm.ProactiveQueueManager()
    item = _item()
    prefs: dict = {}
    response = ResponseClassification(responded=True, engagement_score=0.8, response_valence=0.7)
    rt.update_queue_from_response(item, response, mgr, prefs)
    assert item.status == ItemStatus.RESPONDED.value
    assert item.user_engaged is True
    assert mgr.base_priority(item.item_type) > qm.BASE_PRIORITY_BY_TYPE[item.item_type]
    assert prefs["proactive_goal_check_in_enabled"] is True


def test_ignored_response_reduces_priority_and_counts():
    mgr = qm.ProactiveQueueManager()
    item = _item()
    response = ResponseClassification(responded=False)
    rt.update_queue_from_response(item, response, mgr, {})
    assert item.status == ItemStatus.IGNORED.value
    assert item.user_engaged is False
    assert mgr.base_priority(item.item_type) < qm.BASE_PRIORITY_BY_TYPE[item.item_type]
    assert mgr.get_ignore_count(item.item_type) == 1


def test_three_consecutive_ignores_disables_type():
    mgr = qm.ProactiveQueueManager()
    prefs: dict = {}
    for _ in range(3):
        rt.update_queue_from_response(_item(), ResponseClassification(responded=False), mgr, prefs)
    assert prefs["proactive_goal_check_in_enabled"] is False
