import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import infra.db.models as models
from infra.db.engine import make_session_factory, init_db, session_scope


def _shared_sqlite_engine():
    # StaticPool + check_same_thread=False so the FastAPI worker thread sees the seeded in-memory DB.
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    return engine
from infra.db.goal_store import PostgresGoalStore
from infra.db.memory_store import PostgresMemoryStore
from infra.db.safety_store import PostgresSafetyLog
from infra.db.onboarding_store import PostgresOnboardingStore
from backend.layer7_goals.schemas import Goal
from backend.layer2_memory.schemas import EpisodicMemory, SemanticMemory
from backend.layer11_safety.schemas import CrisisSignal
from api.dependencies import get_state
from api.routes.goals import router as goals_router
from api.routes.memory import router as memory_router
from api.routes.safety import router as safety_router
from api.routes.onboarding import router as onboarding_router
from api.routes.sessions import router as sessions_router


def _client():
    factory = make_session_factory(_shared_sqlite_engine())
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user",
                            config={"onboarding": {"graduation_sessions": 5}})
    app = FastAPI()
    for r in (goals_router, memory_router, safety_router, onboarding_router, sessions_router):
        app.include_router(r)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), factory


def test_goals_list_get_create():
    client, f = _client()
    PostgresGoalStore(f, "local-user").add_goal(Goal(goal_id="g1", title="run 5k", status="active"))
    assert client.get("/goals").json()[0]["title"] == "run 5k"
    assert client.get("/goals/g1").json()["goal_id"] == "g1"
    assert client.get("/goals/nope").status_code == 404
    created = client.post("/goals", json={"title": "learn guitar"})
    assert created.status_code == 201 and created.json()["title"] == "learn guitar"
    assert client.post("/goals", json={"title": "   "}).status_code == 422   # empty title rejected


def test_memory_audit_and_get():
    client, f = _client()
    store = PostgresMemoryStore(f)
    mem = EpisodicMemory(user_id="local-user", summary="hiking trip")
    store.save_episodic(mem)
    store.save_semantic(SemanticMemory(user_id="local-user", statement="likes tea"))
    audit = client.get("/memory/audit").json()
    assert audit["episodic"][0]["summary"] == "hiking trip"
    assert audit["semantic"][0]["statement"] == "likes tea"
    assert client.get(f"/memory/{mem.memory_id}").json()["summary"] == "hiking trip"
    assert client.get("/memory/00000000-0000-0000-0000-000000000000").status_code == 404


def test_safety_events():
    client, f = _client()
    PostgresSafetyLog(f).record(CrisisSignal(user_id="local-user", tier="tier_2", confidence=0.6))
    body = client.get("/safety/events").json()
    assert body[0]["tier"] == "tier_2" and body[0]["confidence"] == 0.6


def test_onboarding_status():
    client, f = _client()
    PostgresOnboardingStore(f, "local-user").record_turn("s1")
    body = client.get("/onboarding").json()
    assert body["cold_start_active"] is True and body["session_index"] == 1


def test_sessions_list():
    client, f = _client()
    with session_scope(f) as s:
        s.add(models.Session(user_id="local-user", session_key="s1", turn_count=3))
    body = client.get("/sessions").json()
    assert body[0]["session_key"] == "s1" and body[0]["turn_count"] == 3
