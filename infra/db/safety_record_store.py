"""Postgres-backed Layer-11 Safety Record — the tamper-evident SHA-256 hash chain (§8).

Wraps the real, in-memory ``backend.layer11_safety.safety_record.SafetyRecord`` rather than
reimplementing its chain math: on each append, prior entries are loaded into a fresh in-memory
``SafetyRecord``, the real ``.append()``/``.verify_chain()`` methods do the actual work, and only
the new entry is persisted. Distinct from ``PostgresSafetyLog`` (the raw ``CrisisSignal`` dump
that feeds SC-4's dependency monitor) -- this is the formal, verifiable accountability record.
"""
from __future__ import annotations

from typing import Optional

from backend.layer11_safety.safety_record import SafetyRecord
from backend.layer11_safety.schemas import SafetyRecordEntry
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresSafetyRecordStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def _load(self) -> SafetyRecord:
        record = SafetyRecord(self._user_id)
        with session_scope(self._sf) as s:
            rows = (s.query(m.SafetyRecordEntry).filter_by(user_id=self._user_id)
                    .order_by(m.SafetyRecordEntry.id.asc()).all())
            record.entries = [from_jsonable(SafetyRecordEntry, dict(r.payload)) for r in rows]
        return record

    def append(self, entry_type: str, detail: str = "", tier: Optional[str] = None,
               session_id: Optional[str] = None, content: str = "", now=None) -> SafetyRecordEntry:
        record = self._load()
        entry = record.append(entry_type, detail=detail, tier=tier, session_id=session_id,
                              content=content, now=now)
        with session_scope(self._sf) as s:
            s.add(m.SafetyRecordEntry(
                user_id=self._user_id, entry_id=entry.entry_id, payload=to_jsonable(entry)))
        return entry

    def verify_chain(self) -> bool:
        return self._load().verify_chain()
