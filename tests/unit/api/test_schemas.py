import pytest
pytest.importorskip("pydantic")

from api.schemas import ChatRequest, ChatResponse


def test_chat_request_defaults_session_none():
    req = ChatRequest(message="hi")
    assert req.message == "hi" and req.session_id is None


def test_chat_response_roundtrips():
    resp = ChatResponse(response="hey", conversation_mode="casual", cognitive_system="system1",
                        crisis_active=False, refined=False, session_id="s1")
    assert resp.model_dump()["response"] == "hey"


def test_chat_request_requires_message():
    with pytest.raises(Exception):
        ChatRequest()
