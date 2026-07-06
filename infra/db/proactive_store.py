"""Postgres-backed Layer-6 proactive queue — durable outreach candidates.

Persists Layer-6 ``ProactiveItem`` domain objects (JSONB payload keyed by ``item_id``) so the
proactive queue survives restarts and the scheduler's proactive-check job can load, re-prioritize,
and write items back. Bound to one user; all queries are user-scoped.
"""
from __future__ import annotations

from typing import Optional

from backend.layer6_proactivity.schemas import ProactiveItem
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresProactiveQueue:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def upsert(self, item: ProactiveItem) -> str:
        with session_scope(self._sf) as s:
            row = s.query(m.ProactiveItem).filter_by(
                item_id=item.item_id, user_id=self._user_id).one_or_none()
            payload = to_jsonable(item)
            if row is None:
                s.add(m.ProactiveItem(
                    user_id=self._user_id, item_id=item.item_id, item_type=item.item_type,
                    status=item.status, payload=payload))
            else:
                row.item_type = item.item_type
                row.status = item.status
                row.payload = payload
        return item.item_id

    def save_all(self, items) -> None:
        for item in items or []:
            self.upsert(item)

    def load(self, statuses: Optional[list] = None) -> list[ProactiveItem]:
        with session_scope(self._sf) as s:
            q = s.query(m.ProactiveItem).filter_by(user_id=self._user_id)
            if statuses is not None:
                q = q.filter(m.ProactiveItem.status.in_(list(statuses)))
            rows = q.order_by(m.ProactiveItem.id.asc()).all()
            return [from_jsonable(ProactiveItem, dict(r.payload)) for r in rows]
