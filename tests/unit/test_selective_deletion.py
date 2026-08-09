"""Tests for SC-2 Selective Deletion (architecture doc §4)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.layer12_privacy import selective_deletion as sd
from backend.layer12_privacy.schemas import (
    CascadeImpactReport,
    DeletionCertificate,
    DeletionScope,
    DeletionType,
)

NOW = datetime(2025, 6, 1, 12, 0)


class FakeMemoryStore:
    def __init__(self, memories):
        self._m = {m.memory_id: m for m in memories}
    def all(self):
        return list(self._m.values())
    def get(self, mid):
        return self._m.get(mid)
    def update(self, mid, fields):
        for k, v in fields.items():
            setattr(self._m[mid], k, v)
    def delete(self, mid):
        self._m.pop(mid, None)


def _mem(mid, tags=None, person=None, content="some content"):
    return SimpleNamespace(memory_id=mid, topic_tags=tags or [], person_name=person, content=content)


def _store():
    return FakeMemoryStore([
        _mem("m1", tags=["arjun", "relationships"], person="Arjun"),
        _mem("m2", tags=["arjun"], person="Arjun"),
        _mem("m3", tags=["work"]),
    ])


# ── Request construction (§4.1) ──────────────────────────────────────────────
def test_create_request_sets_confirmation_and_undo_window():
    req = sd.create_deletion_request("u1", DeletionType.SINGLE_MEMORY.value,
                                     DeletionScope(memory_id="m1"), now=NOW)
    assert req.confirmation_required == "standard"
    assert req.undo_window_expiry == NOW + timedelta(hours=1)


def test_full_wipe_is_irreversible():
    req = sd.create_deletion_request("u1", DeletionType.FULL_WIPE.value,
                                     DeletionScope(full_wipe_confirmed=True), now=NOW)
    assert req.undo_window_expiry == NOW                       # zero undo window
    assert req.confirmation_required == "extra_plus_passphrase"


def test_identity_memory_has_24h_window_and_extra_confirmation():
    req = sd.create_deletion_request("u1", DeletionType.IDENTITY_MEMORY.value,
                                     DeletionScope(identity_entry_ids=["b1"]), now=NOW)
    assert req.undo_window_expiry == NOW + timedelta(hours=24)
    assert req.confirmation_required == "extra"


# ── Scope resolution (§4.3) ──────────────────────────────────────────────────
def test_topic_scope_resolves_matching_memories():
    req = sd.create_deletion_request("u1", DeletionType.TOPIC_BASED.value,
                                     DeletionScope(topic_tags=["arjun"]), now=NOW)
    ids = sd.resolve_scope(req.scope, req.deletion_type, _store())
    assert set(ids) == {"m1", "m2"}


def test_full_wipe_scope_resolves_everything():
    req = sd.create_deletion_request("u1", DeletionType.FULL_WIPE.value,
                                     DeletionScope(full_wipe_confirmed=True), now=NOW)
    assert set(sd.resolve_scope(req.scope, req.deletion_type, _store())) == {"m1", "m2", "m3"}


# ── Dry run cascade (§4.4) ───────────────────────────────────────────────────
def test_dry_run_reports_cascade_for_semantic_facts():
    # SemanticMemory's real fields are memory_id/statement/supporting_episode_ids -- a prior
    # mismatch here (fact_id/fact_text/derived_from_episodes) would have raised AttributeError
    # the first time a real semantic_store was ever passed in (docs/POLISH_BACKLOG.md).
    store = _store()
    semantic = SimpleNamespace(all=lambda: [
        SimpleNamespace(memory_id="f1", statement="knows Arjun", supporting_episode_ids=["m1", "m2"]),
        SimpleNamespace(memory_id="f2", statement="likes work", supporting_episode_ids=["m3", "x9"]),
    ])
    req = sd.create_deletion_request("u1", DeletionType.TOPIC_BASED.value,
                                     DeletionScope(topic_tags=["arjun"]), now=NOW)
    report = sd.dry_run_deletion(req, store, semantic_store=semantic)
    assert isinstance(report, CascadeImpactReport)
    assert report.memories_deleted == 2
    # f1 derived only from m1,m2 (both deleted) → will_be_deleted
    assert ("f1", "knows Arjun", "will_be_deleted") in report.semantic_facts_affected
    assert req.dry_run_completed is True


def test_dry_run_marks_partially_cited_fact_for_update():
    store = _store()
    semantic = SimpleNamespace(all=lambda: [
        SimpleNamespace(memory_id="f1", statement="x", supporting_episode_ids=["m1", "keep1"]),
    ])
    req = sd.create_deletion_request("u1", DeletionType.TOPIC_BASED.value,
                                     DeletionScope(topic_tags=["arjun"]), now=NOW)
    report = sd.dry_run_deletion(req, store, semantic_store=semantic)
    assert ("f1", "x", "will_be_updated") in report.semantic_facts_affected


# ── Execution (§4.3) ─────────────────────────────────────────────────────────
def test_execute_requires_confirmed_and_dry_run():
    store = _store()
    req = sd.create_deletion_request("u1", DeletionType.SINGLE_MEMORY.value,
                                     DeletionScope(memory_id="m1"), now=NOW)
    with pytest.raises(ValueError):
        sd.execute_deletion(req, store)            # not confirmed / no dry run


def test_execute_deletes_and_returns_certificate():
    store = _store()
    req = sd.create_deletion_request("u1", DeletionType.SINGLE_MEMORY.value,
                                     DeletionScope(memory_id="m1"), now=NOW)
    sd.dry_run_deletion(req, store)
    req.status = "confirmed"
    cert = sd.execute_deletion(req, store, now=NOW)
    assert isinstance(cert, DeletionCertificate)
    assert cert.deleted_count == 1 and "m1" in cert.deleted_ids
    assert store.get("m1") is None and store.get("m3") is not None
    assert cert.payload_hash and cert.signature


def test_execute_secure_zeros_before_delete():
    store = _store()
    zeroed = {}
    store.update = lambda mid, fields: zeroed.update({mid: fields})  # capture the zeroing write
    req = sd.create_deletion_request("u1", DeletionType.SINGLE_MEMORY.value,
                                     DeletionScope(memory_id="m1"), now=NOW)
    sd.dry_run_deletion(req, store)
    req.status = "confirmed"
    sd.execute_deletion(req, store, now=NOW)
    assert "m1" in zeroed
    assert all(ch == "\x00" for ch in zeroed["m1"]["content"])     # content overwritten with nulls


def test_execute_logs_to_audit():
    store = _store()
    log = []
    req = sd.create_deletion_request("u1", DeletionType.SINGLE_MEMORY.value,
                                     DeletionScope(memory_id="m1"), now=NOW)
    sd.dry_run_deletion(req, store)
    req.status = "confirmed"
    sd.execute_deletion(req, store, audit_log=log, now=NOW)
    assert len(log) == 1 and log[0]["memory_count"] == 1
