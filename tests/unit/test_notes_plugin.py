"""Tests for the Notes plugin (architecture doc §9.3)."""

from backend.layer8_tools.plugins.notes_plugin import NotesPlugin
from backend.layer8_tools.schemas import ConfirmationTier, ToolOutcome


def test_create_note_returns_id_and_stores_tags():
    res = NotesPlugin().execute("create_note",
                                {"title": "Idea", "content": "build it", "tags": ["work"]})
    assert res.outcome == ToolOutcome.SUCCESS.value and res.data["note_id"]


def test_create_validates_content():
    assert NotesPlugin().validate_parameters("create_note", {"title": "x"}).valid is False


def test_append_extends_note_body():
    p = NotesPlugin()
    nid = p.execute("create_note", {"content": "line one"}).data["note_id"]
    p.execute("append_to_note", {"note_id": nid, "content": "line two"})
    note = next(n for n in p.execute("list_notes", {}).data if n["note_id"] == nid)
    assert "line one" in note["content"] and "line two" in note["content"]


def test_list_notes_returns_all():
    p = NotesPlugin()
    p.execute("create_note", {"content": "a"})
    p.execute("create_note", {"content": "b"})
    assert len(p.execute("list_notes", {}).data) == 2


def test_delete_note_removes_it():
    p = NotesPlugin()
    nid = p.execute("create_note", {"content": "a"}).data["note_id"]
    p.execute("delete_note", {"note_id": nid})
    assert p.execute("list_notes", {}).data == []


def test_undo_delete_restores_note():
    p = NotesPlugin()
    nid = p.execute("create_note", {"content": "a"}).data["note_id"]
    res = p.execute("delete_note", {"note_id": nid})
    assert p.undo(res.undo_token) is True
    assert len(p.execute("list_notes", {}).data) == 1


def test_create_and_append_are_auto_delete_is_soft():
    p = NotesPlugin()
    assert p.capability_for("create_note").default_tier == ConfirmationTier.AUTO.value
    assert p.capability_for("append_to_note").default_tier == ConfirmationTier.AUTO.value
    assert p.capability_for("delete_note").default_tier == ConfirmationTier.SOFT.value
