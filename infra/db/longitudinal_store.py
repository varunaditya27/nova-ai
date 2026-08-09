"""Postgres-backed Layer-10 longitudinal store — durable weekly summaries, narrative arcs,
behavioral patterns, life-calendar entries, and retrospectives.

``LongitudinalSummary`` (JSONB payload keyed by ``summary_id``) is reused for both weekly
summaries (``period="weekly"``) and the single per-user narrative arc (``period="narrative_arc"``)
— its own docstring already scoped it for "weekly summary or narrative chapter". Patterns,
calendar entries, and retrospectives get their own tables, one row per artifact, mirroring
``PostgresSocialStore``'s shape. Bound to one user; all queries are user-scoped.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.layer10_longitudinal.schemas import (
    BehavioralPattern, CalendarEntry, LifeEvent, NarrativeArc, RetrospectivePacket, WeeklySummary,
    YearInReview,
)
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable

_NARRATIVE_ARC_ID = "narrative_arc"   # one row per user; a stable summary_id keeps it a singleton


class PostgresLongitudinalStore:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)

    # ── SC-2 Weekly summaries ────────────────────────────────────────────────
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

    # ── SC-1 Narrative arc (one row per user) ────────────────────────────────
    def load_narrative_arc(self) -> Optional[NarrativeArc]:
        with session_scope(self._sf) as s:
            row = s.query(m.LongitudinalSummary).filter_by(
                summary_id=_NARRATIVE_ARC_ID, user_id=self._user_id).one_or_none()
            return from_jsonable(NarrativeArc, dict(row.payload)) if row else None

    def save_narrative_arc(self, arc: NarrativeArc) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.LongitudinalSummary).filter_by(
                summary_id=_NARRATIVE_ARC_ID, user_id=self._user_id).one_or_none()
            payload = to_jsonable(arc)
            if row is None:
                s.add(m.LongitudinalSummary(
                    user_id=self._user_id, summary_id=_NARRATIVE_ARC_ID,
                    period="narrative_arc", payload=payload))
            else:
                row.payload = payload

    # ── SC-4 Year in Review (one row per user per year) ──────────────────────
    def save_year_in_review(self, review: YearInReview) -> None:
        summary_id = f"year_in_review_{review.year}"
        with session_scope(self._sf) as s:
            row = s.query(m.LongitudinalSummary).filter_by(
                summary_id=summary_id, user_id=self._user_id).one_or_none()
            payload = to_jsonable(review)
            if row is None:
                s.add(m.LongitudinalSummary(
                    user_id=self._user_id, summary_id=summary_id,
                    period="year_in_review", payload=payload))
            else:
                row.payload = payload

    def load_year_in_review(self, year: int) -> Optional[YearInReview]:
        with session_scope(self._sf) as s:
            row = s.query(m.LongitudinalSummary).filter_by(
                summary_id=f"year_in_review_{year}", user_id=self._user_id).one_or_none()
            return from_jsonable(YearInReview, dict(row.payload)) if row else None

    # ── SC-3 Behavioral patterns ──────────────────────────────────────────────
    def save_patterns(self, patterns: list[BehavioralPattern]) -> None:
        with session_scope(self._sf) as s:
            for pattern in patterns:
                row = s.query(m.BehavioralPattern).filter_by(
                    pattern_id=pattern.pattern_id, user_id=self._user_id).one_or_none()
                payload = to_jsonable(pattern)
                if row is None:
                    s.add(m.BehavioralPattern(
                        user_id=self._user_id, pattern_id=pattern.pattern_id,
                        is_active=True, payload=payload))
                else:
                    row.payload = payload

    def active_patterns(self) -> list[BehavioralPattern]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.BehavioralPattern)
                    .filter_by(user_id=self._user_id, is_active=True).all())
            return [from_jsonable(BehavioralPattern, dict(r.payload)) for r in rows]

    def deactivate_patterns(self, pattern_ids: list[str]) -> None:
        if not pattern_ids:
            return
        with session_scope(self._sf) as s:
            (s.query(m.BehavioralPattern)
             .filter(m.BehavioralPattern.user_id == self._user_id,
                     m.BehavioralPattern.pattern_id.in_(pattern_ids))
             .update({"is_active": False}, synchronize_session=False))

    # ── SC-5 Life calendar ────────────────────────────────────────────────────
    def calendar_entries(self) -> list[CalendarEntry]:
        with session_scope(self._sf) as s:
            rows = s.query(m.LifeCalendarEntry).filter_by(user_id=self._user_id).all()
            return [from_jsonable(CalendarEntry, dict(r.payload)) for r in rows]

    def save_calendar_entries(self, entries: list[CalendarEntry]) -> None:
        with session_scope(self._sf) as s:
            for entry in entries:
                row = s.query(m.LifeCalendarEntry).filter_by(
                    entry_id=entry.entry_id, user_id=self._user_id).one_or_none()
                payload = to_jsonable(entry)
                if row is None:
                    s.add(m.LifeCalendarEntry(
                        user_id=self._user_id, entry_id=entry.entry_id,
                        has_fired=entry.has_fired, payload=payload))
                else:
                    row.has_fired = entry.has_fired
                    row.payload = payload

    # ── SC-4 Retrospectives ───────────────────────────────────────────────────
    def save_retrospective(self, packet: RetrospectivePacket) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.Retrospective).filter_by(
                packet_id=packet.packet_id, user_id=self._user_id).one_or_none()
            payload = to_jsonable(packet)
            if row is None:
                s.add(m.Retrospective(
                    user_id=self._user_id, packet_id=packet.packet_id,
                    has_been_surfaced=packet.has_been_surfaced, payload=payload))
            else:
                row.has_been_surfaced = packet.has_been_surfaced
                row.payload = payload

    def pending_retrospectives(self) -> list[RetrospectivePacket]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.Retrospective)
                    .filter_by(user_id=self._user_id, has_been_surfaced=False).all())
            return [from_jsonable(RetrospectivePacket, dict(r.payload)) for r in rows]

    def mark_retrospective_surfaced(self, packet_id: str, now=None) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.Retrospective).filter_by(
                packet_id=packet_id, user_id=self._user_id).one_or_none()
            if row is None:
                return
            payload = dict(row.payload)
            payload["has_been_surfaced"] = True
            payload["surfaced_at"] = (now or datetime.now(timezone.utc)).isoformat()
            row.has_been_surfaced = True
            row.payload = payload

    # ── Life events (chapter-boundary detection input, Layer10ContextPacket.recent_life_event) ──
    def save_life_event(self, event: LifeEvent) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.LifeEventRow).filter_by(
                event_id=event.event_id, user_id=self._user_id).one_or_none()
            payload = to_jsonable(event)
            if row is None:
                s.add(m.LifeEventRow(
                    user_id=self._user_id, event_id=event.event_id,
                    event_date=event.event_date.isoformat(), payload=payload))
            else:
                row.event_date = event.event_date.isoformat()
                row.payload = payload

    def life_events(self) -> list[LifeEvent]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.LifeEventRow).filter_by(user_id=self._user_id)
                    .order_by(m.LifeEventRow.event_date.desc()).all())
            return [from_jsonable(LifeEvent, dict(r.payload)) for r in rows]
