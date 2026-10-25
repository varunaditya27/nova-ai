"""A session is a stretch of conversation, not a page load: the server owns the boundary."""
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.routes.chat import router as chat_router
from api.routes.relationship import router as relationship_router
from api.session_resolver import resolve_session_id
from api.state import build_app_state
from infra.db.engine import init_db


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "ok"
    def stream(self, prompt, **k):
        yield "ok"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _state():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    return build_app_state(
        config={"system": {"default_user_id": "u1"}, "llm": {}, "memory": {}},
        llm_clients=clients, engine=engine, vector_store=object())


def _client(state):
    app = FastAPI()
    app.state.nova = state
    app.include_router(chat_router)
    app.include_router(relationship_router)
    return TestClient(app, raise_server_exceptions=False)


def test_reloading_the_page_mid_conversation_is_not_a_new_session():
    state = _state()
    client = _client(state)
    first = client.post("/chat", json={"message": "hello", "session_id": "tab-1"}).json()
    second = client.post("/chat", json={"message": "hello again", "session_id": "tab-2"}).json()
    assert first["session_id"] == second["session_id"] == "tab-1"
    assert client.get("/relationship").json()["total_sessions"] == 1


def test_first_message_adopts_the_clients_id():
    assert resolve_session_id(_state(), "mine") == "mine"


def test_silence_beyond_the_gap_starts_a_new_session():
    state = _state()
    client = _client(state)
    first = client.post("/chat", json={"message": "hello"}).json()["session_id"]
    later = datetime.now(timezone.utc) + timedelta(minutes=31)
    assert resolve_session_id(state, first, now=later) != first
    assert resolve_session_id(state, first, now=datetime.now(timezone.utc)) == first
