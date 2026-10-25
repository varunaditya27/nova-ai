import pytest
pytest.importorskip("fastapi")

from types import SimpleNamespace
from fastapi.testclient import TestClient

import api.main as main


def test_app_boots_and_chat_works(monkeypatch):
    class Orch:
        def run_turn(self, user_id, message, now=None, session_id="", client_metadata=None):
            return SimpleNamespace(response_text="hello from nova", conversation_mode="casual",
                                   cognitive_system="system1", crisis_active=False, refined=False)
    from tests.unit.api.test_chat import _empty_session_factory
    fake_state = SimpleNamespace(default_user_id="local-user", orchestrator=Orch(),
                                 engine=None, config={"api": {"cors_origins": []}},
                                 session_factory=_empty_session_factory())
    monkeypatch.setattr(main, "build_app_state", lambda: fake_state)

    app = main.create_app()
    with TestClient(app) as client:      # triggers lifespan startup
        assert client.get("/health").status_code == 200
        r = client.post("/chat", json={"message": "hi"})
        assert r.status_code == 200 and r.json()["response"] == "hello from nova"


def test_cors_origins_read_from_config(monkeypatch):
    """The `api.cors_origins` config knob must actually drive CORS — a frontend on a non-default
    origin (e.g. Vite :5173) has to be configurable without a code change."""
    monkeypatch.setattr(main, "load_config",
                        lambda *a, **k: {"api": {"cors_origins": ["https://app.example.com"]}})
    assert main._cors_origins() == ["https://app.example.com"]


def test_cors_origins_falls_back_when_config_unreadable(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("no config")
    monkeypatch.setattr(main, "load_config", _boom)
    assert main._cors_origins() == ["http://localhost:3000"]
