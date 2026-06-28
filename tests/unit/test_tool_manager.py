"""Tests for SC: Tool Manager (architecture doc §5 — orchestration end-to-end)."""

from backend.layer8_tools.tool_manager import ToolManager
from backend.layer8_tools.plugins.calendar_plugin import CalendarPlugin
from backend.layer8_tools.plugins.email_plugin import EmailPlugin
from backend.layer8_tools.plugins.web_search_plugin import WebSearchPlugin
from backend.layer8_tools.schemas import ActionType, ToolIntent, ToolOutcome


def _manager(intent=None, **plugins):
    m = ToolManager(intent_fn=(lambda msg: intent) if intent is not None else None)
    for p in plugins.values() or [CalendarPlugin(), EmailPlugin()]:
        m.register_plugin(p)
    return m


# ── Registration + routing (§5) ──────────────────────────────────────────────
def test_register_and_get_plugin():
    m = ToolManager()
    cal = CalendarPlugin()
    m.register_plugin(cal)
    assert m.get_plugin("calendar") is cal


def test_no_intent_means_not_invoked():
    m = ToolManager()
    m.register_plugin(CalendarPlugin())
    out = m.process("just chatting about my day", user_id="u1")
    assert out.tool_invoked is False


# ── AUTO path executes immediately (§5, §4) ──────────────────────────────────
def test_auto_op_executes_and_records():
    intent = ToolIntent("web_search", "search", ActionType.SEARCH.value, {"query": "python"})
    m = ToolManager(intent_fn=lambda msg: intent)
    m.register_plugin(WebSearchPlugin(search_fn=lambda q: [{"title": "T", "url": "https://e.com"}]))
    out = m.process("search for python", user_id="u1")
    assert out.tool_invoked is True
    assert out.result.outcome == ToolOutcome.SUCCESS.value
    assert out.action_record is not None
    assert m.recorder.get_action_history()[0].tool_name == "web_search"


# ── HARD path gates on confirmation (§4) ─────────────────────────────────────
def test_hard_op_requires_confirmation_first():
    intent = ToolIntent("email", "send", ActionType.SEND.value, {"draft_id": "d1"})
    m = ToolManager(intent_fn=lambda msg: intent)
    m.register_plugin(EmailPlugin())
    out = m.process("send that email", user_id="u1")
    assert out.confirmation_request is not None
    assert out.result is None                         # not executed yet


def test_hard_op_executes_after_confirmation():
    email = EmailPlugin()
    did = email.execute("draft", {"to": "a@b.com", "body": "hi"}).data["draft_id"]
    intent = ToolIntent("email", "send", ActionType.SEND.value, {"draft_id": did})
    m = ToolManager(intent_fn=lambda msg: intent)
    m.register_plugin(email)
    out = m.process("yes send it", user_id="u1", confirmed=True)
    assert out.tool_invoked is True
    assert out.result.outcome == ToolOutcome.SUCCESS.value


# ── Missing-parameter path asks one question (§6) ────────────────────────────
def test_missing_param_returns_clarification():
    intent = ToolIntent("calendar", "create_event", ActionType.CREATE.value, {"title": "Dentist"})
    m = ToolManager(intent_fn=lambda msg: intent)
    m.register_plugin(CalendarPlugin())
    out = m.process("put the dentist on my calendar", user_id="u1")
    assert out.clarification_question is not None
    assert out.result is None


# ── Direct execution + validation (§5) ───────────────────────────────────────
def test_execute_tool_records_action():
    m = ToolManager()
    m.register_plugin(CalendarPlugin())
    res = m.execute_tool("calendar", "create_event",
                         {"title": "A", "start": "2026-07-01T09:00"}, user_id="u1")
    assert res.outcome == ToolOutcome.SUCCESS.value
    assert m.recorder.get_action_history()[0].operation == "create_event"


def test_execute_tool_invalid_params_fails_without_executing():
    m = ToolManager()
    m.register_plugin(CalendarPlugin())
    res = m.execute_tool("calendar", "create_event", {"title": "A"}, user_id="u1")  # no start
    assert res.outcome == ToolOutcome.FAILURE.value


def test_unknown_tool_returns_failure():
    m = ToolManager()
    res = m.execute_tool("nonexistent", "do", {}, user_id="u1")
    assert res.outcome == ToolOutcome.FAILURE.value


# ── Undo through the uniform interface (§7) ──────────────────────────────────
def test_undo_action_reverses_and_marks_undone():
    m = ToolManager()
    cal = CalendarPlugin()
    m.register_plugin(cal)
    m.execute_tool("calendar", "create_event",
                   {"title": "A", "start": "2026-07-01T09:00"}, user_id="u1")
    action_id = m.recorder.get_action_history()[0].action_id
    assert m.undo_action(action_id) is True
    assert cal.execute("list_events", {}).data == []
    assert m.recorder.get_action_history()[0].undone is True


# ── Keyword intent fallback (§5) ─────────────────────────────────────────────
def test_keyword_detect_web_search():
    m = ToolManager()
    m.register_plugin(WebSearchPlugin(search_fn=lambda q: []))
    out = m.process("search for the weather tomorrow", user_id="u1")
    assert out.tool_invoked is True and out.result.tool_name == "web_search"
