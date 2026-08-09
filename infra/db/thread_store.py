"""Postgres-backed Layer-1 narrative-thread store (architecture doc §3.5).

``backend/layer1_input/thread_tracker.py``'s ``ThreadStore`` Protocol is deliberately read-only
(``get_all`` only) -- per its own docstring, "thread records are created and resolved by the
Layer 2 State Updater," i.e. a post-turn writer, not Layer 1 itself. This store implements both
halves: the real write path (``save``/``mark_status``) for the post-turn thread writer, and the
``get_all`` read method ``thread_tracker.due_candidates``/``get_due_threads`` need. Bound to one
user -- the Protocol has no ``user_id`` param, so callers pre-scope an instance per user, the
same convention as ``api/assembly.py``'s ``_SingleProfileStore``.
"""
from __future__ import annotations

from typing import Optional

from backend.layer1_input.schemas import NarrativeThread, ThreadStatus
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresThreadStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def save(self, thread: NarrativeThread) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.NarrativeThreadRow).filter_by(
                thread_id=str(thread.thread_id), user_id=self._user_id).one_or_none()
            payload = to_jsonable(thread)
            if row is None:
                s.add(m.NarrativeThreadRow(
                    user_id=self._user_id, thread_id=str(thread.thread_id),
                    status=thread.status, follow_up_due_at=thread.follow_up_due_at,
                    payload=payload))
            else:
                row.status = thread.status
                row.follow_up_due_at = thread.follow_up_due_at
                row.payload = payload

    def get_all(self, status: Optional[ThreadStatus] = None) -> list[NarrativeThread]:
        with session_scope(self._sf) as s:
            q = s.query(m.NarrativeThreadRow).filter_by(user_id=self._user_id)
            if status is not None:
                q = q.filter_by(status=status.value if hasattr(status, "value") else status)
            return [from_jsonable(NarrativeThread, dict(r.payload)) for r in q.all()]

    def mark_status(self, thread_id, status: ThreadStatus) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.NarrativeThreadRow).filter_by(
                thread_id=str(thread_id), user_id=self._user_id).one_or_none()
            if row is None:
                return
            row.status = status.value
            payload = dict(row.payload)
            payload["status"] = status.value
            row.payload = payload
