"""LLM-backed tool intent: keyword-gated routing + small-model parameter extraction."""
import json

from backend.layer8_tools.llm_intent import make_llm_intent_fn

# The real capability param requirements for the plugins under test.
_REQUIRED = {
    ("email", "draft"): ["to", "body"],
    ("web_search", "search"): ["query"],
    ("reminders", "create_reminder"): ["text", "due"],
}


def _required_for(tool, op):
    return _REQUIRED.get((tool, op), [])


def test_non_tool_message_returns_none():
    """No tool keyword → not a tool turn. The LLM is never even consulted (no chat hijacking)."""
    calls = []
    fn = make_llm_intent_fn(lambda p: calls.append(p) or "{}", _required_for)
    assert fn("how are you feeling today?") is None
    assert calls == []                       # LLM not called for a non-tool message


def test_email_params_extracted_by_llm():
    fn = make_llm_intent_fn(
        lambda p: '```json\n{"to": "sam@example.com", "body": "I will be late"}\n```',
        _required_for)
    intent = fn("email sam@example.com and say I will be late")
    assert intent["tool_name"] == "email" and intent["operation"] == "draft"
    assert intent["parameters"] == {"to": "sam@example.com", "body": "I will be late"}


def test_llm_failure_degrades_to_keyword_behavior():
    """A raising/garbage LLM must never crash the turn — routing still works, params empty."""
    def boom(_):
        raise RuntimeError("model down")
    intent = make_llm_intent_fn(boom, _required_for)("send email to my boss")
    assert intent["tool_name"] == "email" and intent["parameters"] == {}


def test_web_search_query_seeded_even_without_llm_params():
    """web_search must never regress below the deterministic keyword query extraction."""
    intent = make_llm_intent_fn(lambda p: "{}", _required_for)("search for guitar chords")
    assert intent["tool_name"] == "web_search"
    assert intent["parameters"]["query"] == "guitar chords"


def test_non_required_keys_are_dropped():
    fn = make_llm_intent_fn(
        lambda p: json.dumps({"to": "a@b.com", "body": "hi", "cc": "x@y.com", "junk": 1}),
        _required_for)
    intent = fn("email a@b.com saying hi")
    assert set(intent["parameters"]) == {"to", "body"}     # cc/junk not in required → dropped
