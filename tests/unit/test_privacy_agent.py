"""Tests for the Privacy Agent coordinator + ConsentManager (architecture doc §7)."""

from types import SimpleNamespace

import pytest

from backend.layer12_privacy.privacy_agent import PrivacyAgent
from backend.layer12_privacy.schemas import (
    ConsentRecord,
    DeletionCertificate,
    DeletionScope,
    DeletionType,
    MemoryAuditView,
)


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


def _mem(mid, tags=None):
    return SimpleNamespace(memory_id=mid, topic_tags=tags or [], content="c",
                           importance_score=0.5, is_anchored=False, created_at=None,
                           human_readable_summary="s", emotion_at_formation="neutral",
                           reinforcement_count=0)


def _agent():
    return PrivacyAgent("u1", memory_store=FakeMemoryStore([_mem("m1", ["arjun"]), _mem("m2")]))


# ── Consent management (§7) ──────────────────────────────────────────────────
def test_record_and_check_consent():
    agent = _agent()
    rec = agent.record_consent("cloud_backup_sync", granted=True)
    assert isinstance(rec, ConsentRecord)
    assert agent.is_consent_active("cloud_backup_sync") is True


def test_latest_consent_wins_on_revoke():
    agent = _agent()
    agent.record_consent("usage_telemetry", granted=True)
    agent.record_consent("usage_telemetry", granted=False)
    assert agent.is_consent_active("usage_telemetry") is False


def test_unset_consent_is_inactive():
    assert _agent().is_consent_active("cloud_backup_sync") is False


def test_non_revocable_consent_cannot_be_revoked():
    agent = _agent()
    agent.record_consent("crisis_session_logging", granted=True)
    with pytest.raises(ValueError):
        agent.record_consent("crisis_session_logging", granted=False)


# ── Deletion orchestration (§7) ──────────────────────────────────────────────
def test_deletion_flow_produces_certificate():
    agent = _agent()
    req = agent.request_deletion(DeletionType.SINGLE_MEMORY.value, DeletionScope(memory_id="m1"))
    assert req.dry_run_completed is True
    req.status = "confirmed"
    cert = agent.execute_deletion(req)
    assert isinstance(cert, DeletionCertificate) and cert.deleted_count == 1
    assert agent.memory_store.get("m1") is None


def test_deletion_is_logged():
    agent = _agent()
    req = agent.request_deletion(DeletionType.SINGLE_MEMORY.value, DeletionScope(memory_id="m1"))
    req.status = "confirmed"
    agent.execute_deletion(req)
    assert any(e.get("request_id") == req.request_id for e in agent.audit_log)


# ── Audit + integrity delegation (§7) ────────────────────────────────────────
def test_generate_audit_returns_view():
    assert isinstance(_agent().generate_audit(), MemoryAuditView)


def test_verify_integrity_detects_tamper():
    agent = _agent()
    result = agent.verify_integrity([{"id": 1}], stored_root="0" * 64)
    assert result.status == "TAMPER_DETECTED"
