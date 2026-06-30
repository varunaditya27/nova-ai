"""Tests for SC-4 Cross-Platform Sync (architecture doc §6)."""

from datetime import datetime

from backend.layer12_privacy import encryption_manager as em
from backend.layer12_privacy import sync_coordinator as sc
from backend.layer12_privacy.schemas import SyncDelta, SyncOperation

KEY = em.derive_master_key("sync pass", b"salt" * 4, iterations=2000)


def _coord(device="phone"):
    return sc.SyncCoordinator(user_id="u1", device_id=device, sync_key=KEY)


def _op(store, rid="r1", record=None, op_type="upsert_semantic"):
    return SyncOperation(operation_type=op_type, record_id=rid, store_name=store,
                         serialized_record=record or {}, timestamp=datetime(2025, 6, 1))


# ── Zero-knowledge deltas (§6.2-6.3) ─────────────────────────────────────────
def test_delta_payload_is_encrypted_no_plaintext():
    ops = [_op("episodic_memories", record={"summary": "secret diary entry about Arjun"})]
    delta = _coord().build_delta(ops)
    assert isinstance(delta, SyncDelta)
    assert "secret diary entry" not in delta.encrypted_payload     # server sees only ciphertext
    assert delta.payload_size_bytes > 0


def test_delta_round_trips_via_decrypt():
    ops = [_op("episodic_memories", rid="m1", record={"summary": "walked the dog"})]
    coord = _coord()
    delta = coord.build_delta(ops)
    restored = coord.decrypt_delta(delta)
    assert restored[0].record_id == "m1"
    assert restored[0].serialized_record["summary"] == "walked the dog"


def test_other_device_can_decrypt_with_same_key():
    ops = [_op("semantic_facts", record={"fact_text": "likes tea"})]
    delta = _coord("phone").build_delta(ops)
    restored = _coord("laptop").decrypt_delta(delta)
    assert restored[0].serialized_record["fact_text"] == "likes tea"


def test_wrong_key_cannot_decrypt():
    delta = _coord().build_delta([_op("semantic_facts", record={"fact_text": "x"})])
    other = sc.SyncCoordinator(user_id="u1", device_id="evil",
                               sync_key=em.derive_master_key("wrong", b"salt" * 4, iterations=2000))
    import pytest
    with pytest.raises(em.DecryptionError):
        other.decrypt_delta(delta)


# ── Conflict resolution (§6.4) ───────────────────────────────────────────────
def test_episodic_always_inserts():
    op = _op("episodic_memories", record={"summary": "new"}, op_type="upsert_episodic")
    assert sc.resolve_conflict(op, local_record=None).action == "insert"


def test_semantic_last_write_wins_remote_newer():
    op = _op("semantic_facts", record={"fact_text": "v2", "last_updated_at": "2025-06-02"})
    res = sc.resolve_conflict(op, local_record={"fact_text": "v1", "last_updated_at": "2025-06-01"})
    assert res.action == "overwrite"


def test_semantic_keeps_local_when_local_newer():
    op = _op("semantic_facts", record={"fact_text": "v2", "last_updated_at": "2025-06-01"})
    res = sc.resolve_conflict(op, local_record={"fact_text": "v1", "last_updated_at": "2025-06-03"})
    assert res.action == "keep_local"


def test_identity_conflict_holds_for_user_resolution():
    op = _op("identity_beliefs", record={"content": "values privacy"})
    res = sc.resolve_conflict(op, local_record={"content": "values openness"})
    assert res.action == "hold_pending_user_resolution"


def test_personality_vector_weighted_merge():
    op = _op("personality_vector",
             record={"traits": {"warmth": 0.8}, "interaction_count": 100})
    res = sc.resolve_conflict(op, local_record={"traits": {"warmth": 0.4}, "interaction_count": 300})
    # weighted: (0.8*100 + 0.4*300) / 400 = 0.5
    assert res.action == "overwrite"
    assert abs(res.record["traits"]["warmth"] - 0.5) < 1e-9
    assert res.record["interaction_count"] == 400


def test_longitudinal_keeps_more_complete():
    op = _op("weekly_summaries", record={"narrative_summary": "a much longer richer summary"})
    res = sc.resolve_conflict(op, local_record={"narrative_summary": "short"})
    assert res.action == "overwrite"
