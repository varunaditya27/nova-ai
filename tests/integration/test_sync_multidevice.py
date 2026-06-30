"""Integration: Layer 12 zero-knowledge multi-device sync + integrity.

Drives the real encryption manager, sync coordinator, and integrity verifier together: device A
builds an encrypted delta the server cannot read, device B (same key) decrypts it, conflict
resolution is applied, and a Merkle integrity check confirms the synced store is untampered.
"""

from datetime import datetime

import pytest

from backend.layer12_privacy import encryption_manager as em
from backend.layer12_privacy import integrity_verifier as iv
from backend.layer12_privacy import sync_coordinator as sc
from backend.layer12_privacy.schemas import SyncDelta, SyncOperation

KEY = em.derive_master_key("shared device passphrase", b"salt" * 4, iterations=2000)


def _op(record, rid="m1", store="episodic_memories", op_type="upsert_episodic"):
    return SyncOperation(operation_type=op_type, record_id=rid, store_name=store,
                         serialized_record=record, timestamp=datetime(2025, 6, 1))


def test_server_never_sees_plaintext_but_other_device_decrypts():
    device_a = sc.SyncCoordinator(user_id="u1", device_id="phone", sync_key=KEY)
    device_b = sc.SyncCoordinator(user_id="u1", device_id="laptop", sync_key=KEY)

    delta = device_a.build_delta([_op({"summary": "private diary entry about Arjun"})])
    assert isinstance(delta, SyncDelta)
    assert "private diary entry" not in delta.encrypted_payload      # zero-knowledge server

    restored = device_b.decrypt_delta(delta)                         # same key → round-trips
    assert restored[0].serialized_record["summary"] == "private diary entry about Arjun"


def test_wrong_key_device_cannot_decrypt():
    delta = sc.SyncCoordinator("u1", "phone", KEY).build_delta([_op({"summary": "secret"})])
    evil = sc.SyncCoordinator("u1", "evil",
                              em.derive_master_key("wrong", b"salt" * 4, iterations=2000))
    with pytest.raises(em.DecryptionError):
        evil.decrypt_delta(delta)


def test_semantic_conflict_resolves_last_write_wins():
    remote = _op({"fact_text": "v2", "last_updated_at": "2025-06-03"},
                 store="semantic_facts", op_type="upsert_semantic")
    res = sc.resolve_conflict(remote, local_record={"fact_text": "v1", "last_updated_at": "2025-06-01"})
    assert res.action == "overwrite"


def test_integrity_check_detects_tampering_post_sync():
    records = [{"id": "m1", "v": "a"}, {"id": "m2", "v": "b"}]
    root = iv.compute_merkle_root(records)
    assert iv.run_check(records, stored_root=root).status == "INTACT"
    tampered = [{"id": "m1", "v": "a"}, {"id": "m2", "v": "HACKED"}]
    assert iv.run_check(tampered, stored_root=root).status == "TAMPER_DETECTED"
