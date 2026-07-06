"""Postgres-backed zero-knowledge sync store (Layer 12, server side).

The server is a blind relay: it persists opaque encrypted deltas (produced on-device by
``SyncCoordinator.build_delta``) with only routing metadata, and hands each device the deltas it
has not yet applied — deltas from *other* devices, past the device's cursor. It never decrypts.
The row ``id`` is the monotonic pull cursor. Bound to one user; all queries are user-scoped.
"""
from __future__ import annotations

from typing import Optional

import infra.db.models as m
from infra.db.engine import session_scope


class PostgresSyncStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def push(self, delta_id: str, source_device: str, seq: int, payload: str,
             size_bytes: Optional[int] = None) -> bool:
        """Store one encrypted delta. Idempotent on delta_id (a re-pushed delta is a no-op)."""
        with session_scope(self._sf) as s:
            exists = s.query(m.SyncDelta).filter_by(delta_id=delta_id).one_or_none()
            if exists is not None:
                return False
            s.add(m.SyncDelta(
                user_id=self._user_id, delta_id=delta_id, source_device=source_device,
                seq=int(seq or 0), payload=payload,
                size_bytes=int(size_bytes if size_bytes is not None else len(payload or ""))))
            return True

    def pull(self, device_id: str, after_cursor: int = 0) -> tuple[list[dict], int]:
        """Return (deltas, new_cursor): deltas from OTHER devices past ``after_cursor``, in order.
        The cursor is the max server id returned (or the input cursor when nothing is new)."""
        with session_scope(self._sf) as s:
            rows = (s.query(m.SyncDelta)
                    .filter(m.SyncDelta.user_id == self._user_id,
                            m.SyncDelta.source_device != device_id,
                            m.SyncDelta.id > int(after_cursor or 0))
                    .order_by(m.SyncDelta.id.asc()).all())
            deltas = [{"cursor": r.id, "delta_id": r.delta_id, "source_device": r.source_device,
                       "seq": r.seq, "encrypted_payload": r.payload, "size_bytes": r.size_bytes}
                      for r in rows]
        new_cursor = deltas[-1]["cursor"] if deltas else int(after_cursor or 0)
        return deltas, new_cursor

    def status(self) -> dict:
        with session_scope(self._sf) as s:
            rows = s.query(m.SyncDelta).filter_by(user_id=self._user_id).all()
            by_device: dict[str, int] = {}
            latest = 0
            for r in rows:
                by_device[r.source_device] = by_device.get(r.source_device, 0) + 1
                latest = max(latest, r.id)
            return {"total_deltas": len(rows), "by_device": by_device, "latest_cursor": latest}
