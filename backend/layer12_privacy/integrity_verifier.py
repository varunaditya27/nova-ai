"""SC-1 — Integrity Verifier: Merkle tamper detection (architecture doc §3.4).

Runs daily. Builds a Merkle tree over every record in the memory stores and compares the root
against the one anchored in secure storage. A mismatch beyond expected writes/deletions means the
data was modified outside Nova — the user is alerted (paranoia is a feature). Leaf hashes are
sorted so the root is order-independent (records returned in any order verify identically).
Deterministic; pure stdlib.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime
from typing import Optional

from backend.layer12_privacy.schemas import IntegrityCheckResult

_EMPTY_ROOT = hashlib.sha256(b"NOVA_MERKLE_EMPTY").hexdigest()


def _serialize(record) -> str:
    if dataclasses.is_dataclass(record):
        record = dataclasses.asdict(record)
    try:
        return json.dumps(record, sort_keys=True, default=str)
    except TypeError:
        return str(record)


def _leaf(record) -> str:
    return hashlib.sha256(_serialize(record).encode("utf-8")).hexdigest()


def compute_merkle_root(records: list) -> str:
    """Compute the order-independent Merkle root of a set of records (architecture doc §3.4)."""
    if not records:
        return _EMPTY_ROOT
    level = sorted(_leaf(r) for r in records)
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left   # promote odd leaf
            nxt.append(hashlib.sha256((left + right).encode("utf-8")).hexdigest())
        level = nxt
    return level[0]


def detect_tampering(records: list, stored_root: str) -> bool:
    """True if the recomputed root no longer matches the anchored root."""
    return compute_merkle_root(records) != stored_root


def run_check(records: list, stored_root: str, now: Optional[datetime] = None) -> IntegrityCheckResult:
    """Compare the current Merkle root against the stored root (architecture doc §3.4)."""
    current = compute_merkle_root(records)
    if current == stored_root:
        return IntegrityCheckResult(status="INTACT", checked_at=now or datetime.utcnow(),
                                    current_root=current, expected_root=stored_root)
    return IntegrityCheckResult(
        status="TAMPER_DETECTED", checked_at=now or datetime.utcnow(),
        current_root=current, expected_root=stored_root,
        mismatch_details="Merkle root mismatch beyond expected writes/deletions.")
