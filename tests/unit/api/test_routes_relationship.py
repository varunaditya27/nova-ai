import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from infra.db.engine import make_session_factory, init_db
from infra.db.relationship_store import PostgresRelationshipStore
from api.dependencies import get_state
from api.routes.relationship import router


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), factory


def test_relationship_defaults_to_new():
    client, _ = _client()
    body = client.get("/relationship").json()
    assert body["stage"] == "new" and body["total_messages_exchanged"] == 0


def test_relationship_reflects_recorded_turns():
    client, factory = _client()
    store = PostgresRelationshipStore(factory, "local-user")
    for i in range(4):
        store.record_turn(f"s{i}")
    body = client.get("/relationship").json()
    assert body["stage"] == "acquaintance" and body["total_sessions"] == 4
