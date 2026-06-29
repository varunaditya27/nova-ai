"""Tests for SC: Tool Manager (architecture doc §5 — orchestration end-to-end).

Includes the security model (§5.1): confirmation tokens are bound to the exact action and
user, single-use (anti-replay), the direct execution path is fail-closed on gated tiers, and
undo enforces ownership.
"""

from backend.layer8_tools.tool_manager import ToolManager
from backend.layer8_tools.plugins.calendar_plugin import CalendarPlugin
from backend.layer8_tools.plugins.email_plugin import EmailPlugin
from backend.layer8_tools.plugins.reminders_plugin import RemindersPlugin
from backend.layer8_tools.plugins.web_search_plugin import WebSearchPlugin
from backend.layer8_tools.schemas import ActionType, ToolIntent, ToolOutcome


def _mgr(intent=None, *plugins):
    m = ToolManager(intent_fn=(lambda msg: intent) if intent is not None else None)
    for p in plugins:
        m.register_plugin(p)
    return m


# ── Registration + routing (§5) ──────────────────────────────────────────────
def test_register_and_get_plugin():
    m = ToolManager()
    cal = CalendarPlugin()
    m.register_plugin(cal)
    assert m.get_plugin("calendar") is cal


def test_no_intent_means_not_invoked():
    m = _mgr(None, CalendarPlugin())
    out = m.process("just chatting about my day", user_id="u1")
    assert out.tool_invoked is False


# ── AUTO path executes immediately (§5, §4) ──────────────────────────────────
def test_auto_op_executes_and_records():
    intent = ToolIntent("web_search", "search", ActionType.SEARCH.value, {"query": "python"})
    m = _mgr(intent, WebSearchPlugin(search_fn=lambda q: [{"title": "T", "url": "https://e.com"}]))
    out = m.process("search for python", user_id="u1")
    assert out.tool_invoked is True
    assert out.result.outcome == ToolOutcome.SUCCESS.value
    assert out.action_record is not None
    assert m.recorder.get_action_history()[0].tool_name == "web_search"


# ── HARD path gates on confirmation (§4) ─────────────────────────────────────
def test_hard_op_requires_confirmation_first():
    intent = ToolIntent("email", "send", ActionType.SEND.value, {"draft_id": "d1"})
    m = _mgr(intent, EmailPlugin())
    out = m.process("send that email", user_id="u1")
    assert out.confirmation_request is not None
    assert out.result is None                         # not executed yet


def test_hard_op_executes_via_confirm_action():
    email = EmailPlugin()
    did = email.execute("draft", {"to": "a@b.com", "body": "hi"}).data["draft_id"]
    intent = ToolIntent("email", "send", ActionType.SEND.value, {"draft_id": did})
    m = _mgr(intent, email)
    pending = m.process("send it", user_id="u1")
    out = m.confirm_action(pending.confirmation_request.request_id, user_id="u1")
    assert out.tool_invoked is True and out.result.outcome == ToolOutcome.SUCCESS.value


# ── Confirmation token security (§5.1) ───────────────────────────────────────
def test_confirmation_token_is_single_use():
    intent = ToolIntent("calendar", "delete_event", ActionType.DELETE.value, {"event_id": "x"})
    m = _mgr(intent, CalendarPlugin())
    rid = m.process("delete it", user_id="u1").confirmation_request.request_id
    m.confirm_action(rid, user_id="u1")
    replay = m.confirm_action(rid, user_id="u1")      # same token again
    assert replay.tool_invoked is False               # replay rejected


def test_confirmation_ownership_enforced():
    intent = ToolIntent("calendar", "delete_event", ActionType.DELETE.value, {"event_id": "x"})
    m = _mgr(intent, CalendarPlugin())
    rid = m.process("delete it", user_id="u1").confirmation_request.request_id
    assert m.confirm_action(rid, user_id="u2").tool_invoked is False   # not the owner
    # token survives the impostor and still works for the rightful owner
    assert m.confirm_action(rid, user_id="u1").tool_invoked is True


def test_token_cannot_authorize_a_different_action():
    # A token issued for deleting event X must not authorize deleting event Y (confused deputy).
    intent = ToolIntent("calendar", "delete_event", ActionType.DELETE.value, {"event_id": "X"})
    m = _mgr(intent, CalendarPlugin())
    rid = m.process("delete X", user_id="u1").confirmation_request.request_id
    res = m.execute_tool("calendar", "delete_event", {"event_id": "Y"},
                         user_id="u1", confirmation_id=rid)
    assert res.outcome == ToolOutcome.FAILURE.value   # fingerprint mismatch → blocked


# ── Missing-parameter path asks one question (§6) ────────────────────────────
def test_missing_param_returns_clarification():
    intent = ToolIntent("calendar", "create_event", ActionType.CREATE.value, {"title": "Dentist"})
    m = _mgr(intent, CalendarPlugin())
    out = m.process("put the dentist on my calendar", user_id="u1")
    assert out.clarification_question is not None
    assert out.result is None


# ── Direct execution is fail-CLOSED on gated tiers (§5.1) ────────────────────
def test_execute_tool_auto_records_action():
    m = _mgr(None, CalendarPlugin())
    res = m.execute_tool("calendar", "find_free_time", {"duration": 30}, user_id="u1")  # AUTO
    assert res.outcome == ToolOutcome.SUCCESS.value
    assert m.recorder.get_action_history()[0].operation == "find_free_time"


def test_execute_tool_blocks_gated_without_token():
    m = _mgr(None, EmailPlugin())
    res = m.execute_tool("email", "send", {"draft_id": "d1"}, user_id="u1")  # HARD, no token
    assert res.outcome == ToolOutcome.FAILURE.value
    assert "confirmation" in (res.error_message or "").lower()


def test_execute_tool_gated_with_valid_token_executes():
    cal = CalendarPlugin()
    eid = cal.execute("create_event", {"title": "A", "start": "2026-07-01T09:00"}).data["event_id"]
    intent = ToolIntent("calendar", "delete_event", ActionType.DELETE.value, {"event_id": eid})
    m = _mgr(intent, cal)
    rid = m.process("delete it", user_id="u1").confirmation_request.request_id
    res = m.execute_tool("calendar", "delete_event", {"event_id": eid},
                         user_id="u1", confirmation_id=rid)
    assert res.outcome == ToolOutcome.SUCCESS.value


def test_execute_tool_invalid_params_fails_without_executing():
    m = _mgr(None, CalendarPlugin())
    res = m.execute_tool("calendar", "find_free_time", {}, user_id="u1")  # AUTO, missing duration
    assert res.outcome == ToolOutcome.FAILURE.value


def test_unknown_tool_returns_failure():
    res = ToolManager().execute_tool("nonexistent", "do", {}, user_id="u1")
    assert res.outcome == ToolOutcome.FAILURE.value


# ── Undo enforces ownership (§5.1, §7) ───────────────────────────────────────
def test_undo_action_reverses_and_marks_undone():
    m = _mgr(None, RemindersPlugin())
    m.execute_tool("reminders", "create_reminder",
                   {"text": "a", "due": "2026-07-01T09:00"}, user_id="u1")  # AUTO + undoable
    action_id = m.recorder.get_action_history()[0].action_id
    assert m.undo_action(action_id, user_id="u1") is True
    assert m.get_plugin("reminders").execute("list_reminders", {}).data == []
    assert m.recorder.get_action_history()[0].undone is True


def test_undo_rejects_non_owner():
    m = _mgr(None, RemindersPlugin())
    m.execute_tool("reminders", "create_reminder",
                   {"text": "a", "due": "2026-07-01T09:00"}, user_id="u1")
    action_id = m.recorder.get_action_history()[0].action_id
    assert m.undo_action(action_id, user_id="u2") is False        # not the owner
    assert len(m.get_plugin("reminders").execute("list_reminders", {}).data) == 1  # untouched


# ── Keyword intent fallback (§5) ─────────────────────────────────────────────
def test_keyword_detect_web_search():
    m = _mgr(None, WebSearchPlugin(search_fn=lambda q: []))
    out = m.process("search for the weather tomorrow", user_id="u1")
    assert out.tool_invoked is True and out.result.tool_name == "web_search"
