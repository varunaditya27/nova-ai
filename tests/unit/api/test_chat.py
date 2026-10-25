import pytest
pytest.importorskip("fastapi")

from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.chat import router
from api.dependencies import get_state, get_orchestrator


def _empty_session_factory():
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from infra.db.engine import init_db, make_session_factory
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    return make_session_factory(engine)


def _client(out=None, raises=False):
    app = FastAPI()

    class Orch:
        def run_turn(self, user_id, message, now=None, session_id="", client_metadata=None):
            if raises:
                raise RuntimeError("boom")
            return out
    app.include_router(router)
    app.dependency_overrides[get_state] = lambda: SimpleNamespace(
        default_user_id="local-user", config={}, session_factory=_empty_session_factory())
    app.dependency_overrides[get_orchestrator] = lambda: Orch()
    return TestClient(app, raise_server_exceptions=False)


def test_chat_returns_response_shape():
    out = SimpleNamespace(response_text="hey there", conversation_mode="casual",
                          cognitive_system="system1", crisis_active=False, refined=False,
                          session_id="s1")
    r = _client(out=out).post("/chat", json={"message": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["response"] == "hey there" and body["cognitive_system"] == "system1"


def test_chat_response_includes_stream_parity_fields():
    """`/chat` JSON must carry the same turn metadata the SSE `meta` frame exposes
    (confabulation_guard) plus crisis_tier, so a frontend sees one consistent contract."""
    out = SimpleNamespace(response_text="hey", conversation_mode="crisis",
                          cognitive_system="system2", crisis_active=True, crisis_tier="tier_2",
                          refined=True, tool_invoked=False, confabulation_guard=True)
    body = _client(out=out).post("/chat", json={"message": "hi"}).json()
    assert body["confabulation_guard"] is True
    assert body["crisis_tier"] == "tier_2"


def test_chat_returns_echoes_from_recalled_memories():
    """The memories Nova recalled this turn surface as 'echoes' on the response (Principle 7)."""
    mem = SimpleNamespace(summary="you said you'd regret choosing Mongo", created_at=None)
    out = SimpleNamespace(response_text="right", conversation_mode="casual",
                          cognitive_system="system1", crisis_active=False, refined=False,
                          tool_invoked=False, confabulation_guard=False, recalled_memories=[mem])
    body = _client(out=out).post("/chat", json={"message": "databases again"}).json()
    assert body["echoes"] and body["echoes"][0]["summary"].startswith("you said")


def test_chat_503_on_orchestrator_error():
    r = _client(raises=True).post("/chat", json={"message": "hi"})
    assert r.status_code == 503


def test_chat_rejects_empty_message():
    c = _client(out=SimpleNamespace(response_text="x", conversation_mode="casual",
                                    cognitive_system="system1", crisis_active=False, refined=False))
    assert c.post("/chat", json={"message": "   "}).status_code == 422
    assert c.post("/chat/stream", json={"message": ""}).status_code == 422


def test_chat_stream_emits_sse_and_reconstructs_text():
    out = SimpleNamespace(response_text="Hey there. Nice to see you!", delivered="Hey there. Nice to see you!",
                          conversation_mode="casual", cognitive_system="system1",
                          crisis_active=False, refined=False, confabulation_guard=False)
    r = _client(out=out).post("/chat/stream", json={"message": "hi", "session_id": "s1"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    import json
    events = []
    for block in r.text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        name = next(l.split(":", 1)[1].strip() for l in block.splitlines() if l.startswith("event:"))
        data = next(l.split(":", 1)[1].strip() for l in block.splitlines() if l.startswith("data:"))
        events.append((name, json.loads(data)))

    assert events[0][0] == "meta" and events[0][1]["session_id"] == "s1"
    assert events[-1][0] == "done"
    text = "".join(e[1]["token"] for e in events if e[0] == "token")
    assert text == "Hey there. Nice to see you!"
