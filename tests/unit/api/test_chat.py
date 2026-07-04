import pytest
pytest.importorskip("fastapi")

from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.chat import router
from api.dependencies import get_state, get_orchestrator


def _client(out=None, raises=False):
    app = FastAPI()

    class Orch:
        def run_turn(self, user_id, message, now=None, session_id=""):
            if raises:
                raise RuntimeError("boom")
            return out
    app.include_router(router)
    app.dependency_overrides[get_state] = lambda: SimpleNamespace(default_user_id="local-user")
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


def test_chat_503_on_orchestrator_error():
    r = _client(raises=True).post("/chat", json={"message": "hi"})
    assert r.status_code == 503
