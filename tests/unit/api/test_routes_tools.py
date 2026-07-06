"""End-to-end tool flow over HTTP: /chat detects intent -> confirm -> execute -> history."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from infra.db.engine import make_session_factory, init_db
from api.state import build_tool_manager
from api.dependencies import get_state, get_tool_manager
from api.routes.tools import router as tools_router


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    tm = build_tool_manager(factory, "local-user")
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user", tool_manager=tm)
    app = FastAPI()
    app.include_router(tools_router)
    app.dependency_overrides[get_state] = lambda: state
    app.dependency_overrides[get_tool_manager] = lambda: tm
    return TestClient(app, raise_server_exceptions=False), tm


def test_auto_tool_execution_is_recorded_in_history():
    client, tm = _client()
    # An AUTO web search executes immediately (offline backend → empty results) and is audited.
    out = tm.process("search for puppy training tips", user_id="local-user", session_id="s1")
    assert out.tool_invoked is True
    history = client.get("/tools/history").json()
    assert history and history[0]["tool_name"] == "web_search"
    assert history[0]["outcome"] == "success"


def test_pending_confirm_flow_over_http():
    client, tm = _client()
    from backend.layer8_tools.schemas import ToolIntent
    # Inject a fully-parametrized SOFT action so it lands in the pending queue deterministically.
    tm._intent_fn = lambda msg: ToolIntent(
        tool_name="email", operation="draft",
        parameters={"to": "sam@example.com", "body": "hi"}, confidence=0.9, raw_text=msg)
    out = tm.process("email sam", user_id="local-user", session_id="s1")
    assert out.confirmation_request is not None  # SOFT → needs confirmation

    pending = client.get("/tools/pending").json()
    assert len(pending) == 1 and pending[0]["tool_name"] == "email"
    rid = pending[0]["request_id"]

    res = client.post(f"/tools/confirm/{rid}").json()
    assert res["outcome"] == "success"
    assert any(a["tool_name"] == "email" for a in client.get("/tools/history").json())
    # Token is single-use: the pending entry is gone.
    assert client.get("/tools/pending").json() == []


def test_deny_removes_pending():
    client, tm = _client()
    from backend.layer8_tools.schemas import ToolIntent
    tm._intent_fn = lambda msg: ToolIntent(
        tool_name="email", operation="draft",
        parameters={"to": "a@b.com", "body": "x"}, confidence=0.9, raw_text=msg)
    tm.process("email", user_id="local-user", session_id="s1")
    rid = client.get("/tools/pending").json()[0]["request_id"]
    assert client.post(f"/tools/deny/{rid}").status_code == 200
    assert client.get("/tools/pending").json() == []


def test_pending_reports_real_tier_and_reversibility():
    """GET /tools/pending must reflect the bound action's real gate/reversibility — a HARD,
    irreversible action must not be reported to the frontend as soft/reversible."""
    client, tm = _client()
    from backend.layer8_tools.tool_manager import _Pending
    tm._pending["rid-hard"] = _Pending(
        fingerprint="fp", tool_name="email", operation="send",
        parameters={"to": "x@y.com"}, action_type="write", user_id="local-user",
        session_id="s1", tier="hard", reversible=False)
    pending = client.get("/tools/pending").json()
    assert len(pending) == 1
    assert pending[0]["tier"] == "hard"
    assert pending[0]["reversible"] is False


def test_confirm_unknown_id_is_404():
    client, _ = _client()
    assert client.post("/tools/confirm/nope").status_code == 404


def test_deny_unknown_id_is_404():
    client, _ = _client()
    assert client.post("/tools/deny/nope").status_code == 404
