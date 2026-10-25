"""The desk greets the user by the name Nova learned, and never shows an internal fragment."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.routes.continuity import router
from infra.db.engine import init_db, make_session_factory
from infra.db.initial_state_store import PostgresInitialStateStore


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    app = FastAPI()
    app.state.nova = type("S", (), {"session_factory": factory, "default_user_id": "local-user",
                                    "config": {}})()
    app.include_router(router)
    return TestClient(app), factory


def test_name_is_none_until_learned_then_returned():
    client, factory = _client()
    assert client.get("/home").json()["name"] is None
    store = PostgresInitialStateStore(factory, "local-user")
    state = store.load()
    state.user_handle = "Arjun"
    store.save(state)
    assert client.get("/home").json()["name"] == "Arjun"
