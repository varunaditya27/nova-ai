"""Zero-knowledge sync over HTTP: device A pushes an encrypted delta, device B pulls + decrypts it,
and the server only ever sees ciphertext."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from infra.db.engine import make_session_factory, init_db
from backend.layer12_privacy.sync_coordinator import SyncCoordinator
from backend.layer12_privacy.schemas import SyncDelta, SyncOperation
from api.dependencies import get_state
from api.routes.sync import router as sync_router


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id="local-user")
    app = FastAPI()
    app.include_router(sync_router)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False)


KEY = b"k" * 32


def _push_body(coord: SyncCoordinator, ops):
    d = coord.build_delta(ops)
    return {"delta_id": d.delta_id, "source_device": d.source_device_id, "seq": d.sequence_number,
            "encrypted_payload": d.encrypted_payload, "size_bytes": d.payload_size_bytes}


def test_push_then_pull_on_another_device_roundtrips():
    client = _client()
    a = SyncCoordinator("local-user", "device-A", KEY)
    b = SyncCoordinator("local-user", "device-B", KEY)
    ops = [SyncOperation(operation_type="insert", record_id="m1", store_name="episodic",
                         serialized_record={"summary": "hi"})]
    body = _push_body(a, ops)

    assert client.post("/sync/push", json=body).json()["stored"] is True
    # The stored payload is opaque ciphertext, not the plaintext.
    assert "summary" not in body["encrypted_payload"]

    pulled = client.get("/sync/pull", params={"device_id": _hash("device-B")}).json()
    assert len(pulled["deltas"]) == 1
    got = pulled["deltas"][0]

    # Device B reconstructs the delta and decrypts it back to the original operation.
    delta = SyncDelta(user_id="local-user", source_device_id=got["source_device"],
                      encrypted_payload=got["encrypted_payload"])
    decrypted = b.decrypt_delta(delta)
    assert decrypted[0].record_id == "m1" and decrypted[0].store_name == "episodic"


def test_device_does_not_pull_its_own_deltas():
    client = _client()
    a = SyncCoordinator("local-user", "device-A", KEY)
    body = _push_body(a, [SyncOperation("insert", "m1", "episodic", {"x": 1})])
    client.post("/sync/push", json=body)
    # A pulls with its own (hashed) device id → excluded.
    pulled = client.get("/sync/pull", params={"device_id": body["source_device"]}).json()
    assert pulled["deltas"] == []


def test_push_is_idempotent_on_delta_id():
    client = _client()
    a = SyncCoordinator("local-user", "device-A", KEY)
    body = _push_body(a, [SyncOperation("insert", "m1", "episodic", {"x": 1})])
    assert client.post("/sync/push", json=body).json()["stored"] is True
    assert client.post("/sync/push", json=body).json()["stored"] is False  # duplicate


def test_status_counts_by_device():
    client = _client()
    a = SyncCoordinator("local-user", "device-A", KEY)
    client.post("/sync/push", json=_push_body(a, [SyncOperation("insert", "m1", "episodic", {})]))
    client.post("/sync/push", json=_push_body(a, [SyncOperation("insert", "m2", "episodic", {})]))
    st = client.get("/sync/status").json()
    assert st["total_deltas"] == 2 and st["latest_cursor"] >= 1


def _hash(device_id):
    import hashlib
    return hashlib.sha256(device_id.encode("utf-8")).hexdigest()[:16]
