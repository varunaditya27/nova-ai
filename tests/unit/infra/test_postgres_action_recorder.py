import pytest
pytest.importorskip("sqlalchemy")

from backend.layer8_tools.schemas import ActionRecord, ActionType, ToolOutcome, ToolResult
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.action_recorder import PostgresActionRecorder


def _rec(user="u1"):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresActionRecorder(make_session_factory(engine), user), engine


def test_record_action_persists_and_reads_back():
    rec, _ = _rec()
    aid = rec.record_action(ActionRecord(
        tool_name="reminders", operation="create_reminder",
        action_type=ActionType.CREATE.value, parameters={"text": "call mom"},
        outcome=ToolOutcome.SUCCESS.value, result_summary="created", user_id="u1"))
    history = rec.get_action_history("u1")
    assert len(history) == 1
    assert history[0].action_id == aid
    assert history[0].tool_name == "reminders"
    assert history[0].parameters == {"text": "call mom"}


def test_record_from_result_persists():
    rec, _ = _rec()
    result = ToolResult("notes", "create_note", ToolOutcome.SUCCESS.value,
                        result_summary="saved", undo_token="t1")
    rec.record_from_result(result, action_type=ActionType.CREATE.value,
                           parameters={"body": "x"}, user_id="u1")
    h = rec.get_action_history("u1")
    assert h[0].tool_name == "notes" and h[0].undoable is True


def test_history_is_most_recent_first_and_durable_across_instances():
    rec, engine = _rec()
    for i in range(3):
        rec.record_action(ActionRecord(tool_name="reminders", operation="create_reminder",
                                       user_id="u1", result_summary=f"r{i}"))
    # A fresh recorder over the SAME db (simulating a restart) still sees the history.
    fresh = PostgresActionRecorder(make_session_factory(engine), "u1")
    summaries = [r.result_summary for r in fresh.get_action_history("u1")]
    assert summaries == ["r2", "r1", "r0"]


def test_mark_undone_is_persisted():
    rec, _ = _rec()
    aid = rec.record_action(ActionRecord(tool_name="reminders", operation="delete_reminder",
                                         user_id="u1", undoable=True, undo_token="z"))
    rec.mark_undone(aid)
    assert rec.get_action_history("u1")[0].undone is True


def test_history_is_user_scoped():
    rec, engine = _rec()
    rec.record_action(ActionRecord(tool_name="reminders", operation="x", user_id="u1"))
    other = PostgresActionRecorder(make_session_factory(engine), "u2")
    other.record_action(ActionRecord(tool_name="reminders", operation="y", user_id="u2"))
    assert len(rec.get_action_history("u1")) == 1
    assert len(other.get_action_history("u2")) == 1
