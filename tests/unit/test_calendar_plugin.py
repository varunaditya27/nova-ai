"""Tests for the Calendar plugin (architecture doc §9.1)."""

from backend.layer8_tools.plugins.calendar_plugin import CalendarPlugin
from backend.layer8_tools.schemas import ConfirmationTier, ToolOutcome


def test_create_event_stores_and_returns_id():
    p = CalendarPlugin()
    res = p.execute("create_event", {"title": "Dentist", "start": "2026-07-01T09:00"})
    assert res.outcome == ToolOutcome.SUCCESS.value
    assert res.data["event_id"]
    assert res.undo_token


def test_create_event_validates_required_params():
    assert p_invalid("create_event", {"start": "2026-07-01T09:00"})


def test_list_events_returns_created():
    p = CalendarPlugin()
    p.execute("create_event", {"title": "A", "start": "2026-07-01T09:00"})
    p.execute("create_event", {"title": "B", "start": "2026-07-02T09:00"})
    res = p.execute("list_events", {})
    assert len(res.data) == 2


def test_delete_event_removes_from_active():
    p = CalendarPlugin()
    eid = p.execute("create_event", {"title": "A", "start": "2026-07-01T09:00"}).data["event_id"]
    p.execute("delete_event", {"event_id": eid})
    assert p.execute("list_events", {}).data == []


def test_undo_create_removes_event():
    p = CalendarPlugin()
    res = p.execute("create_event", {"title": "A", "start": "2026-07-01T09:00"})
    assert p.undo(res.undo_token) is True
    assert p.execute("list_events", {}).data == []


def test_undo_delete_restores_event():
    p = CalendarPlugin()
    eid = p.execute("create_event", {"title": "A", "start": "2026-07-01T09:00"}).data["event_id"]
    res = p.execute("delete_event", {"event_id": eid})
    assert p.undo(res.undo_token) is True
    assert len(p.execute("list_events", {}).data) == 1


def test_find_free_time_returns_slots():
    res = CalendarPlugin().execute("find_free_time", {"duration": 30})
    assert res.outcome == ToolOutcome.SUCCESS.value
    assert isinstance(res.data, list)


def test_create_is_soft_delete_is_hard():
    p = CalendarPlugin()
    assert p.capability_for("create_event").default_tier == ConfirmationTier.SOFT.value
    assert p.capability_for("delete_event").default_tier == ConfirmationTier.HARD.value


def p_invalid(operation, params):
    return not CalendarPlugin().validate_parameters(operation, params).valid
