"""Postgres-backed Layer-12 privacy audit — tamper-evident SHA-256 chain of privacy actions.

Records durable, ordered entries (consent changes, deletions) in the ``privacy_audit`` table with a
hash chain (each entry commits to the previous ``entry_hash``), so the deletion log itself cannot be
silently rewritten. Constructed per user; loads the last head on init to continue across restarts.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import infra.db.models as m
from infra.db.engine import session_scope

GENESIS_HASH = "0" * 64


def _entry_hash(prev_hash: str, action: str, detail: dict, ts: str) -> str:
    body = json.dumps({"prev": prev_hash, "action": action, "detail": detail, "ts": ts},
                      sort_keys=True).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


class PostgresPrivacyAudit:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)
        self._head = self._load_head()

    def _load_head(self) -> str:
        with session_scope(self._sf) as s:
            row = (s.query(m.PrivacyAudit).filter_by(user_id=self._user_id)
                   .order_by(m.PrivacyAudit.id.desc()).first())
            return row.entry_hash if row else GENESIS_HASH

    def append(self, action: str, detail: dict) -> str:
        ts = datetime.now(timezone.utc).isoformat()
        h = _entry_hash(self._head, action, detail, ts)
        with session_scope(self._sf) as s:
            s.add(m.PrivacyAudit(user_id=self._user_id, action=action,
                                 detail=json.dumps({"detail": detail, "ts": ts}, sort_keys=True),
                                 prev_hash=self._head, entry_hash=h))
        self._head = h
        return h

    def entries(self) -> list[dict]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.PrivacyAudit).filter_by(user_id=self._user_id)
                    .order_by(m.PrivacyAudit.id.asc()).all())
            return [{"action": r.action, "detail": json.loads(r.detail), "entry_hash": r.entry_hash,
                     "prev_hash": r.prev_hash} for r in rows]

    def verify(self) -> bool:
        prev = GENESIS_HASH
        for e in self.entries():
            d = e["detail"]
            if e["prev_hash"] != prev:
                return False
            if _entry_hash(prev, e["action"], d["detail"], d["ts"]) != e["entry_hash"]:
                return False
            prev = e["entry_hash"]
        return True
