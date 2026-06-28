"""Tests for the Reminders plugin (architecture doc §9.4)."""

from backend.layer8_tools.plugins.reminders_plugin import RemindersPlugin
from backend.layer8_tools.schemas import ConfirmationTier, ToolOutcome


def test_create_reminder_returns_id_and_stores_recurrence():
    res = RemindersPlugin().execute(
        "create_reminder", {"text": "Call mum", "due": "2026-07-01T18:00", "recurrence": "weekly"})
    assert res.outcome == ToolOutcome.SUCCESS.value
    assert res.data["reminder_id"] and res.data["recurrence"] == "weekly"


def test_create_validates_text_and_due():
    assert RemindersPlugin().validate_parameters("create_reminder", {"text": "x"}).valid is False


def test_list_reminders_returns_all():
    p = RemindersPlugin()
    p.execute("create_reminder", {"text": "a", "due": "2026-07-01T09:00"})
    p.execute("create_reminder", {"text": "b", "due": "2026-07-02T09:00"})
    assert len(p.execute("list_reminders", {}).data) == 2


def test_complete_reminder_marks_done():
    p = RemindersPlugin()
    rid = p.execute("create_reminder", {"text": "a", "due": "2026-07-01T09:00"}).data["reminder_id"]
    p.execute("complete_reminder", {"reminder_id": rid})
    r = next(x for x in p.execute("list_reminders", {}).data if x["reminder_id"] == rid)
    assert r["completed"] is True


def test_delete_then_undo_restores():
    p = RemindersPlugin()
    rid = p.execute("create_reminder", {"text": "a", "due": "2026-07-01T09:00"}).data["reminder_id"]
    res = p.execute("delete_reminder", {"reminder_id": rid})
    assert p.undo(res.undo_token) is True
    assert len(p.execute("list_reminders", {}).data) == 1


def test_all_reminder_ops_are_auto_tier():
    p = RemindersPlugin()
    for op in ("create_reminder", "list_reminders", "complete_reminder", "delete_reminder"):
        assert p.capability_for(op).default_tier == ConfirmationTier.AUTO.value
