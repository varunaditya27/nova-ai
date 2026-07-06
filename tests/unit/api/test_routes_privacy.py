"""Layer-12 over HTTP: single-memory deletion (genuine forget + certificate) and integrity."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from infra.db.engine import make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from infra.db.privacy_audit import PostgresPrivacyAudit
from backend.layer2_memory.schemas import EpisodicMemory
from api.dependencies import get_state
from api.routes.memory import router as memory_router


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user", config={})
    app = FastAPI()
    app.include_router(memory_router)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), factory


def test_delete_memory_forgets_and_certifies():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="secret thing", embedding=[0.1, 0.2])
    store.save_episodic(mem)

    resp = client.delete(f"/memory/{mem.memory_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] == 1 and body["certificate"]

    # Genuinely forgotten: gone from the active set and unrecallable (embedding cleared).
    assert store.active_episodic("local-user") == []
    gone = store.get_episodic(mem.memory_id)
    assert gone.is_deleted is True and (gone.embedding in (None, []))
    assert gone.summary == ""

    # A tamper-evident privacy-audit entry was appended.
    audit = PostgresPrivacyAudit(factory, "local-user")
    assert audit.verify() is True
    assert any(e["action"] == "delete_memory" for e in audit.entries())


def test_delete_missing_memory_is_404():
    client, _ = _client()
    assert client.delete("/memory/00000000-0000-0000-0000-000000000000").status_code == 404


def test_double_delete_is_404():
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="x", embedding=[0.1])
    store.save_episodic(mem)
    assert client.delete(f"/memory/{mem.memory_id}").status_code == 200
    assert client.delete(f"/memory/{mem.memory_id}").status_code == 404


def test_get_deleted_memory_is_404():
    """A forgotten memory must read as not-found via GET, not return a zeroed 200 — get_episodic
    returns raw rows (Layer-12 deletion needs them), so the route must honor is_deleted."""
    client, factory = _client()
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="secret", embedding=[0.1, 0.2])
    store.save_episodic(mem)
    assert client.get(f"/memory/{mem.memory_id}").status_code == 200      # present before delete
    assert client.delete(f"/memory/{mem.memory_id}").status_code == 200
    assert client.get(f"/memory/{mem.memory_id}").status_code == 404      # forgotten → not found


def test_integrity_reports_intact_chains():
    client, _ = _client()
    body = client.get("/memory/integrity").json()
    assert body["status"] == "INTACT"
    assert body["audit_chain_ok"] is True and body["privacy_chain_ok"] is True
