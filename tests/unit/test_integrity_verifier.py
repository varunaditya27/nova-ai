"""Tests for SC-1 Integrity Verifier — Merkle tamper detection (architecture doc §3.4)."""

from backend.layer12_privacy import integrity_verifier as iv
from backend.layer12_privacy.schemas import IntegrityCheckResult


def test_merkle_root_is_deterministic():
    records = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
    assert iv.compute_merkle_root(records) == iv.compute_merkle_root(records)


def test_merkle_root_is_order_independent():
    a = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
    b = [{"id": 2, "v": "b"}, {"id": 1, "v": "a"}]
    assert iv.compute_merkle_root(a) == iv.compute_merkle_root(b)


def test_changing_a_record_changes_the_root():
    base = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
    changed = [{"id": 1, "v": "a"}, {"id": 2, "v": "TAMPERED"}]
    assert iv.compute_merkle_root(base) != iv.compute_merkle_root(changed)


def test_empty_store_has_stable_root():
    assert iv.compute_merkle_root([]) == iv.compute_merkle_root([])


def test_run_check_intact_when_root_matches():
    records = [{"id": 1, "v": "a"}]
    root = iv.compute_merkle_root(records)
    result = iv.run_check(records, stored_root=root)
    assert isinstance(result, IntegrityCheckResult) and result.status == "INTACT"


def test_run_check_detects_tampering():
    records = [{"id": 1, "v": "a"}]
    result = iv.run_check(records, stored_root="0" * 64)
    assert result.status == "TAMPER_DETECTED"
    assert result.current_root and result.expected_root == "0" * 64


def test_detect_tampering_boolean():
    records = [{"id": 1, "v": "a"}]
    root = iv.compute_merkle_root(records)
    assert iv.detect_tampering(records, root) is False
    assert iv.detect_tampering(records, "deadbeef") is True
