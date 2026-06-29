"""Tests for the Safety Record — tamper-evident audit trail (architecture doc §8)."""

from backend.layer11_safety.safety_record import SafetyRecord
from backend.layer11_safety.schemas import CrisisTier, SafetyRecordEntry


def _record():
    r = SafetyRecord(user_id="u1")
    r.append("crisis_signal_detected", detail="tier_1 detected", tier=CrisisTier.TIER_1.value,
             session_id="s1", content="user message + response")
    r.append("crisis_response_delivered", detail="resources offered", tier=CrisisTier.TIER_1.value,
             session_id="s1", content="crisis response text")
    return r


def test_append_returns_entry_with_hashes():
    r = SafetyRecord(user_id="u1")
    e = r.append("guardrail_violation", detail="boundary", content="x")
    assert isinstance(e, SafetyRecordEntry)
    assert e.content_hash and e.chain_hash


def test_first_entry_links_to_genesis():
    r = _record()
    assert r.entries[0].previous_entry_hash == SafetyRecord.GENESIS


def test_each_entry_links_to_previous_chain_hash():
    r = _record()
    assert r.entries[1].previous_entry_hash == r.entries[0].chain_hash


def test_intact_chain_verifies():
    assert _record().verify_chain() is True


def test_tampering_breaks_chain():
    r = _record()
    r.entries[0].detail = "tampered: nothing happened"   # mutate a logged entry
    assert r.verify_chain() is False


def test_tampering_with_content_hash_breaks_chain():
    r = _record()
    r.entries[1].content_hash = "0" * 64
    assert r.verify_chain() is False


def test_record_is_append_only():
    r = _record()
    before = len(r.entries)
    r.append("follow_up_scheduled", detail="check-in in 18h", content="schedule")
    assert len(r.entries) == before + 1
    assert not hasattr(r, "delete")               # no deletion API
