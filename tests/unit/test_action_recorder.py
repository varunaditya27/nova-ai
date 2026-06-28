"""Tests for SC: Action Recorder (architecture doc §7 — append-only audit trail)."""

from backend.layer8_tools.action_recorder import ActionRecorder
from backend.layer8_tools.schemas import (
    ActionRecord,
    ActionType,
    ToolOutcome,
    ToolResult,
)


def _rec(tool="calendar", op="create_event", user="u1"):
    return ActionRecord(tool_name=tool, operation=op, action_type=ActionType.CREATE.value,
                        user_id=user, outcome=ToolOutcome.PENDING.value)


def test_record_action_returns_id_and_stores():
    r = ActionRecorder()
    aid = r.record_action(_rec())
    assert aid
    assert r.get_action_history()[0].action_id == aid


def test_history_filters_by_tool():
    r = ActionRecorder()
    r.record_action(_rec(tool="calendar"))
    r.record_action(_rec(tool="email", op="send"))
    assert {a.tool_name for a in r.get_action_history(tool_name="email")} == {"email"}


def test_history_filters_by_user():
    r = ActionRecorder()
    r.record_action(_rec(user="u1"))
    r.record_action(_rec(user="u2"))
    assert {a.user_id for a in r.get_action_history(user_id="u2")} == {"u2"}


def test_record_outcome_updates_record():
    r = ActionRecorder()
    aid = r.record_action(_rec())
    r.record_action_outcome(aid, ToolOutcome.SUCCESS.value, "done")
    rec = r.get_action_history()[0]
    assert rec.outcome == ToolOutcome.SUCCESS.value and rec.result_summary == "done"


def test_link_to_episodic_memory():
    r = ActionRecorder()
    aid = r.record_action(_rec())
    r.link_to_episodic_memory(aid, "mem-42")
    assert r.get_action_history()[0].linked_episodic_memory_id == "mem-42"


def test_record_from_tool_result_marks_undoable():
    r = ActionRecorder()
    result = ToolResult("notes", "create_note", ToolOutcome.SUCCESS.value,
                        result_summary="Note created", undo_token="tok")
    rec = r.record_from_result(result, action_type=ActionType.CREATE.value, user_id="u1")
    assert rec.undoable is True and rec.undo_token == "tok"


def test_undo_is_recorded_not_deleted():
    r = ActionRecorder()
    aid = r.record_action(_rec())
    r.mark_undone(aid)
    history = r.get_action_history()
    assert len(history) == 1 and history[0].undone is True  # still present — audit is append-only


def test_history_is_most_recent_first():
    r = ActionRecorder()
    first = r.record_action(_rec(op="a"))
    second = r.record_action(_rec(op="b"))
    assert [a.action_id for a in r.get_action_history()] == [second, first]
