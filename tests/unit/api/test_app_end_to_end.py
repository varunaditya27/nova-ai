import pytest
pytest.importorskip("fastapi")

from types import SimpleNamespace
from fastapi.testclient import TestClient

import api.main as main


def test_app_boots_and_chat_works(monkeypatch):
    class Orch:
        def run_turn(self, user_id, message, now=None, session_id=""):
            return SimpleNamespace(response_text="hello from nova", conversation_mode="casual",
                                   cognitive_system="system1", crisis_active=False, refined=False)
    fake_state = SimpleNamespace(default_user_id="local-user", orchestrator=Orch(),
                                 engine=None, config={"api": {"cors_origins": []}})
    monkeypatch.setattr(main, "build_app_state", lambda: fake_state)

    app = main.create_app()
    with TestClient(app) as client:      # triggers lifespan startup
        assert client.get("/health").status_code == 200
        r = client.post("/chat", json={"message": "hi"})
        assert r.status_code == 200 and r.json()["response"] == "hello from nova"
