"""Proactive / longitudinal read endpoints + admin job trigger over HTTP."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from infra.db.engine import make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.proactive_store import PostgresProactiveQueue
from backend.layer2_memory.schemas import EpisodicMemory
from backend.layer6_proactivity.schemas import ProactiveItem
from api.dependencies import get_state
from api.routes.proactive import router as proactive_router
from api.routes.longitudinal import router as longitudinal_router
from api.routes.admin import router as admin_router


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user",
                            config={"onboarding": {"graduation_sessions": 5}})
    app = FastAPI()
    for r in (proactive_router, longitudinal_router, admin_router):
        app.include_router(r)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), factory


_NOON_UTC = datetime(2026, 8, 9, 14, 0, tzinfo=timezone.utc)   # afternoon band, no gate races


def test_proactive_suppresses_a_brand_new_relationship():
    """GET /proactive is now genuinely gated (2026-08-09) through the real SC-3 Timing & Delivery
    Gate, not an ungated read of the queue. A relationship with no history at all is "new", and
    block group 3 suppresses all proactive sends for a new relationship (architecture doc §5.1) --
    the exact behavior the prior, ungated version of this endpoint bypassed."""
    client, factory = _client()
    q = PostgresProactiveQueue(factory, "local-user")
    q.upsert(ProactiveItem(item_id="p1", item_type="goal_check_in", status="pending",
                           content_basis="a real, detailed reason to check in on your 5k goal"))
    q.upsert(ProactiveItem(item_id="p2", item_type="silence_break", status="expired"))
    with patch("api.routes.proactive.datetime") as mock_dt:
        mock_dt.now.return_value = _NOON_UTC
        body = client.get("/proactive").json()
    assert body == []


def test_proactive_lists_top_pending_once_the_gate_is_clearable():
    """With an established relationship, a message-free window, and a real (non-vague)
    content_basis, the item clears every one of the gate's five block groups and is surfaced."""
    from infra.db.relationship_store import PostgresRelationshipStore

    client, factory = _client()
    rel_store = PostgresRelationshipStore(factory, "local-user")
    for i in range(20):                          # advances stage well past "new"/"acquaintance"
        rel_store.record_turn(f"s{i}")

    q = PostgresProactiveQueue(factory, "local-user")
    q.upsert(ProactiveItem(item_id="p1", item_type="goal_check_in", status="pending",
                           content_basis="a real, detailed reason to check in on your 5k goal"))
    q.upsert(ProactiveItem(item_id="p2", item_type="silence_break", status="expired"))
    with patch("api.routes.proactive.datetime") as mock_dt:
        mock_dt.now.return_value = _NOON_UTC
        body = client.get("/proactive").json()
    assert [i["item_id"] for i in body] == ["p1"]  # only the gate-passing pending item surfaced


def test_admin_trigger_integrity_job():
    client, _ = _client()
    body = client.post("/admin/jobs/integrity_check").json()
    assert body["job"] == "integrity_check"
    assert body["result"]["status"] == "INTACT"


def test_admin_unknown_job_404():
    client, _ = _client()
    assert client.post("/admin/jobs/nope").status_code == 404


def test_longitudinal_job_then_read_endpoints():
    client, factory = _client()
    PostgresMemoryStore(factory).save_episodic(EpisodicMemory(
        user_id="local-user", summary="a walk", embedding=[0.1],
        created_at=datetime(2026, 7, 3, tzinfo=timezone.utc)))
    with session_scope(factory) as s:
        s.add(models.Session(user_id="local-user", session_key="s1", turn_count=2))

    # No summary yet.
    assert client.get("/longitudinal/latest").status_code == 404
    # Trigger the job, then it's readable.
    ran = client.post("/admin/jobs/longitudinal_summary").json()
    assert ran["result"]["summary_id"]
    assert client.get("/longitudinal/latest").json()["summary_id"] == ran["result"]["summary_id"]
    assert len(client.get("/longitudinal/summaries").json()) == 1
