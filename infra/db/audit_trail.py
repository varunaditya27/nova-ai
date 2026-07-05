"""Postgres-backed tamper-evident audit trail — a drop-in for Layer 2's AuditTrail.

Persists the SHA-256 hash chain to the ``memory_audit`` JSONB table. Constructed per user; loads
the last persisted ``entry_hash`` on init so the chain continues across process restarts.
"""
from __future__ import annotations

from backend.layer2_memory.audit_trail import GENESIS_HASH, compute_event_hash
from backend.layer2_memory.schemas import AuditEvent
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


def _event_type_value(event: AuditEvent) -> str:
    et = event.event_type
    return et.value if hasattr(et, "value") else str(et)


class PostgresAuditTrail:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)
        self._head = self._load_head()

    def _load_head(self) -> str:
        with session_scope(self._sf) as s:
            row = (s.query(m.MemoryAudit).filter_by(user_id=self._user_id)
                   .order_by(m.MemoryAudit.id.desc()).first())
            return row.entry_hash if row else GENESIS_HASH

    def append(self, event: AuditEvent) -> AuditEvent:
        event.user_id = event.user_id or self._user_id
        event.prev_event_hash = self._head
        event.content_hash = compute_event_hash(event)
        with session_scope(self._sf) as s:
            s.add(m.MemoryAudit(
                user_id=self._user_id, entry_hash=event.content_hash,
                prev_hash=event.prev_event_hash, event_type=_event_type_value(event),
                payload=to_jsonable(event)))
        self._head = event.content_hash
        return event

    def verify(self) -> bool:
        with session_scope(self._sf) as s:
            payloads = [r.payload for r in
                        s.query(m.MemoryAudit).filter_by(user_id=self._user_id)
                        .order_by(m.MemoryAudit.id.asc()).all()]
        prev = GENESIS_HASH
        for p in payloads:
            event = from_jsonable(AuditEvent, p)
            if event.prev_event_hash != prev or event.content_hash != compute_event_hash(event):
                return False
            prev = event.content_hash
        return True
