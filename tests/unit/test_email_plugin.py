"""Tests for the Email plugin (architecture doc §9.2)."""

from backend.layer8_tools.plugins.email_plugin import EmailPlugin
from backend.layer8_tools.schemas import ConfirmationTier, ToolOutcome


def test_draft_stores_and_returns_id():
    res = EmailPlugin().execute("draft", {"to": "a@b.com", "subject": "Hi", "body": "Hello"})
    assert res.outcome == ToolOutcome.SUCCESS.value and res.data["draft_id"]


def test_draft_validates_recipient():
    assert EmailPlugin().validate_parameters("draft", {"subject": "Hi", "body": "x"}).valid is False


def test_send_marks_message_sent():
    p = EmailPlugin()
    did = p.execute("draft", {"to": "a@b.com", "subject": "Hi", "body": "Hello"}).data["draft_id"]
    res = p.execute("send", {"draft_id": did})
    assert res.outcome == ToolOutcome.SUCCESS.value and res.data["message_id"]


def test_send_unknown_draft_fails():
    res = EmailPlugin().execute("send", {"draft_id": "nope"})
    assert res.outcome == ToolOutcome.FAILURE.value


def test_undo_draft_removes_it():
    p = EmailPlugin()
    res = p.execute("draft", {"to": "a@b.com", "subject": "Hi", "body": "Hello"})
    assert p.undo(res.undo_token) is True


def test_sent_email_cannot_be_undone():
    p = EmailPlugin()
    did = p.execute("draft", {"to": "a@b.com", "subject": "Hi", "body": "Hello"}).data["draft_id"]
    res = p.execute("send", {"draft_id": did})
    assert p.undo(res.undo_token) is False     # unsend is impossible — hard rule


def test_read_inbox_is_read_only():
    res = EmailPlugin().execute("read_inbox", {})
    assert res.outcome == ToolOutcome.SUCCESS.value and isinstance(res.data, list)


def test_send_is_hard_and_irreversible_draft_is_soft():
    p = EmailPlugin()
    assert p.capability_for("send").default_tier == ConfirmationTier.HARD.value
    assert p.capability_for("send").reversible is False
    assert p.capability_for("draft").default_tier == ConfirmationTier.SOFT.value
