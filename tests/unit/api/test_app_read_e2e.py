import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from infra.db.engine import init_db
from api.state import build_app_state
from api.routes.chat import router as chat_router
from api.routes.goals import router as goals_router
from api.routes.memory import router as memory_router
from api.routes.onboarding import router as onboarding_router


class GoalLLM:
    """system1 returns a goal-extraction JSON; enough for plan/refine/embed too."""
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return '{"goal_detected": true, "new_goal": {"inferred_title": "run a 5k", "confidence": 0.8}}'
    def stream(self, prompt, **k):
        yield "ok"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_chat_write_then_read_end_to_end():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    clients = {"system1": GoalLLM(), "system2": GoalLLM(), "embed": GoalLLM()}
    state = build_app_state(
        config={"system": {"default_user_id": "local-user"}, "llm": {}, "memory": {},
                "onboarding": {"graduation_sessions": 5}},
        llm_clients=clients, engine=engine, vector_store=object())

    app = FastAPI()
    app.state.nova = state
    for r in (chat_router, goals_router, memory_router, onboarding_router):
        app.include_router(r)
    client = TestClient(app, raise_server_exceptions=False)

    # Episodic memory is now promotion-only (docs/layer-2-architecture.md §3.3), checked
    # immediately on arrival. A message containing a life-event keyword triggers promotion
    # deterministically, independent of the stubbed classifier's output, proving the
    # write→audit path end-to-end.
    session_key = "s1"

    resp = client.post("/chat", json={
        "message": "I want to run a 5k next month, I just got the job at the running club",
        "session_id": session_key})
    assert resp.status_code == 200

    # The turn's writes are visible through the read routes (end-to-end).
    goals = client.get("/goals").json()
    assert any(g["title"] == "run a 5k" for g in goals)
    # The promoted turn is summarized by the injected LLM (GoalLLM, a fixed-response stub here),
    # so this only asserts an episode was actually created and is visible end-to-end through the
    # audit route — not on summary content, which depends on the (stubbed) LLM's response.
    audit = client.get("/memory/audit").json()
    assert len(audit["episodic"]) >= 1
    assert client.get("/onboarding").json()["session_index"] == 1
