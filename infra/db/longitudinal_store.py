"""Postgres-backed Layer-10 longitudinal store — durable weekly summaries / narrative artifacts.

Persists Layer-10 ``WeeklySummary`` domain objects (JSONB payload keyed by ``summary_id``) so the
scheduler's weekly longitudinal job has somewhere to write and the read endpoints can serve them.
Bound to one user; all queries are user-scoped.
"""
from __future__ import annotations

from typing import Optional

from backend.layer10_longitudinal.schemas import WeeklySummary
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresLongitudinalStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    def save_summary(self, summary: WeeklySummary, period: str = "weekly") -> str:
        with session_scope(self._sf) as s:
            row = s.query(m.LongitudinalSummary).filter_by(
                summary_id=summary.summary_id, user_id=self._user_id).one_or_none()
            payload = to_jsonable(summary)
            if row is None:
                s.add(m.LongitudinalSummary(
                    user_id=self._user_id, summary_id=summary.summary_id,
                    period=period, payload=payload))
            else:
                row.period = period
                row.payload = payload
        return summary.summary_id

    def summaries(self, period: Optional[str] = None,
                  limit: Optional[int] = None) -> list[WeeklySummary]:
        with session_scope(self._sf) as s:
            q = s.query(m.LongitudinalSummary).filter_by(user_id=self._user_id)
            if period is not None:
                q = q.filter_by(period=period)
            q = q.order_by(m.LongitudinalSummary.id.desc())
            if limit is not None:
                q = q.limit(limit)
            return [from_jsonable(WeeklySummary, dict(r.payload)) for r in q.all()]

    def latest(self, period: str = "weekly") -> Optional[WeeklySummary]:
        got = self.summaries(period=period, limit=1)
        return got[0] if got else None
