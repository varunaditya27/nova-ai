"""SC-5 — Life Calendar (architecture doc §7).

The master temporal index and scheduler for Layer 10. It owns the registry of significant dates
(relationship milestones, life-event anniversaries, weekly/monthly/quarterly triggers), detects
which are due, fires them idempotently, and maps calendar entries to retrospective types for SC-4.
Deterministic and keyed off an injected ``current_date``; in production it runs as the only
persistent Layer 10 loop, checking due dates hourly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from backend.layer10_longitudinal.schemas import (
    CalendarEntry,
    CalendarEntryType,
    Layer6Action,
    LifeEvent,
    RetrospectiveType,
)

# Calendar entry type → retrospective type (architecture doc §7.3).
_ENTRY_TO_RETRO = {
    CalendarEntryType.ANNIVERSARY_1YEAR.value: RetrospectiveType.ONE_YEAR_AGO.value,
    CalendarEntryType.ANNIVERSARY_6MONTH.value: RetrospectiveType.SIX_MONTHS_AGO.value,
    CalendarEntryType.ANNIVERSARY_3MONTH.value: RetrospectiveType.THREE_MONTHS_AGO.value,
    CalendarEntryType.ANNIVERSARY_1MONTH.value: RetrospectiveType.ONE_MONTH_AGO.value,
    CalendarEntryType.LIFE_EVENT_ANNIVERSARY.value: RetrospectiveType.ONE_YEAR_AGO.value,
    CalendarEntryType.GOAL_ANNIVERSARY.value: RetrospectiveType.GOAL_ANNIVERSARY.value,
}

_RELATIONSHIP_MILESTONES = [
    (30, CalendarEntryType.NOVA_RELATIONSHIP_DAY30.value, 0.70),
    (100, CalendarEntryType.NOVA_RELATIONSHIP_DAY100.value, 0.70),
    (365, CalendarEntryType.NOVA_RELATIONSHIP_DAY365.value, 0.90),
]


def map_entry_to_retrospective_type(entry: CalendarEntry) -> Optional[str]:
    return _ENTRY_TO_RETRO.get(entry.entry_type)


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:           # Feb 29 → Feb 28 in a non-leap year
        return d.replace(year=d.year + years, day=28)


class LifeCalendar:
    def __init__(self) -> None:
        self.entries: list[CalendarEntry] = []

    def add_entry(self, entry: CalendarEntry) -> None:
        self.entries.append(entry)

    def register_new_user(self, user_id: str, first_session_date: date) -> None:
        """Register the standard Nova relationship milestones (architecture doc §7.3)."""
        for days, entry_type, priority in _RELATIONSHIP_MILESTONES:
            self.add_entry(CalendarEntry(
                user_id=user_id, date=first_session_date + timedelta(days=days),
                entry_type=entry_type, title=f"Day {days} with Nova", priority=priority,
                layer6_action=Layer6Action(action_type="queue_for_next_session",
                                           urgency="within_week")))

    def register_life_event(self, life_event: LifeEvent) -> None:
        """Register 1/2/3-year anniversaries for a detected life event (architecture doc §7.3)."""
        for years in (1, 2, 3):
            self.add_entry(CalendarEntry(
                user_id=life_event.user_id, date=_add_years(life_event.event_date, years),
                entry_type=CalendarEntryType.LIFE_EVENT_ANNIVERSARY.value,
                title=f"{years} year since: {life_event.title}",
                associated_id=life_event.event_id, priority=life_event.significance_score,
                lookback_days=365 * years,
                layer6_action=Layer6Action(action_type="surface_if_session_opens",
                                           urgency="within_24h")))

    def get_due_entries(self, user_id: str, current_date: date) -> list[CalendarEntry]:
        return [e for e in self.entries
                if e.user_id == user_id and not e.has_fired and e.date <= current_date]

    def fire_entry(self, entry: CalendarEntry, now: Optional[datetime] = None) -> None:
        entry.has_fired = True
        entry.fired_at = now or datetime.utcnow()

    def check_and_fire_due_entries(self, user_id: str, current_date: date) -> list[CalendarEntry]:
        """Fire all due entries for a user; idempotent — fired entries are not re-fired (§7.3)."""
        due = self.get_due_entries(user_id, current_date)
        for entry in due:
            self.fire_entry(entry)
        return due
