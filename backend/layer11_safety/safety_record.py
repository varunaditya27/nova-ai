"""Safety Record — tamper-evident audit trail (architecture doc §8).

Every Layer 11 event is logged to an append-only record whose entries form a SHA-256 hash chain:
each entry's ``chain_hash`` covers its own fields plus the previous entry's ``chain_hash``, so any
later mutation of a logged entry breaks ``verify_chain``. This is the accountability layer — it
makes the safety architecture auditable, not merely claimed. It stores metadata + content *hashes*,
never the raw conversation content (that is covered by Layer 12 privacy).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from backend.layer11_safety.schemas import SafetyRecordEntry


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SafetyRecord:
    GENESIS = "0" * 64

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.entries: list[SafetyRecordEntry] = []

    @staticmethod
    def _chain_hash(entry: SafetyRecordEntry) -> str:
        payload = "|".join([
            entry.entry_id,
            entry.timestamp.isoformat() if entry.timestamp else "",
            entry.entry_type, entry.detail, str(entry.tier),
            str(entry.session_id), entry.content_hash, entry.previous_entry_hash,
        ])
        return _sha256(payload)

    def append(
        self, entry_type: str, detail: str = "", tier: Optional[str] = None,
        session_id: Optional[str] = None, content: str = "", now: Optional[datetime] = None,
    ) -> SafetyRecordEntry:
        """Append an entry, linking it into the tamper-evident chain (architecture doc §8)."""
        previous = self.entries[-1].chain_hash if self.entries else self.GENESIS
        entry = SafetyRecordEntry(
            entry_type=entry_type, detail=detail, tier=tier, session_id=session_id,
            content_hash=_sha256(content), previous_entry_hash=previous,
            timestamp=now or datetime.utcnow())
        entry.chain_hash = self._chain_hash(entry)
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """Recompute the chain and confirm no entry has been altered (architecture doc §8)."""
        previous = self.GENESIS
        for entry in self.entries:
            if entry.previous_entry_hash != previous:
                return False
            if entry.chain_hash != self._chain_hash(entry):
                return False
            previous = entry.chain_hash
        return True
