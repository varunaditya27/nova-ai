"""Tests for SC-5 Life Calendar — scheduling + registration (architecture doc §7)."""

from datetime import date, timedelta

from backend.layer10_longitudinal import life_calendar as lc
from backend.layer10_longitudinal.schemas import (
    CalendarEntry,
    CalendarEntryType,
    LifeEvent,
    RetrospectiveType,
)

FIRST = date(2025, 1, 1)


def _cal():
    return lc.LifeCalendar()


# ── New-user registration (§7.3) ─────────────────────────────────────────────
def test_register_new_user_adds_relationship_milestones():
    cal = _cal()
    cal.register_new_user("u1", FIRST)
    days = sorted((e.date - FIRST).days for e in cal.entries)
    assert days == [30, 100, 365]


# ── Life-event anniversary registration (§7.3) ───────────────────────────────
def test_register_life_event_adds_year_anniversaries():
    cal = _cal()
    ev = LifeEvent(event_id="e1", user_id="u1", title="Started new job",
                   category="career_transition", event_date=FIRST, significance_score=0.9)
    cal.register_life_event(ev)
    years = sorted((e.date.year - FIRST.year) for e in cal.entries)
    assert years == [1, 2, 3]
    assert all(e.entry_type == CalendarEntryType.LIFE_EVENT_ANNIVERSARY.value for e in cal.entries)


# ── Due-entry detection + firing (§7.3) ──────────────────────────────────────
def test_get_due_entries_returns_past_due_unfired():
    cal = _cal()
    cal.add_entry(CalendarEntry(user_id="u1", date=FIRST, entry_type="x"))
    cal.add_entry(CalendarEntry(user_id="u1", date=FIRST + timedelta(days=10), entry_type="y"))
    due = cal.get_due_entries("u1", FIRST + timedelta(days=5))
    assert len(due) == 1 and due[0].entry_type == "x"


def test_check_and_fire_is_idempotent():
    cal = _cal()
    cal.add_entry(CalendarEntry(user_id="u1", date=FIRST, entry_type="x"))
    fired = cal.check_and_fire_due_entries("u1", FIRST + timedelta(days=1))
    assert len(fired) == 1 and fired[0].has_fired is True
    assert cal.check_and_fire_due_entries("u1", FIRST + timedelta(days=1)) == []


def test_entries_for_other_users_are_isolated():
    cal = _cal()
    cal.add_entry(CalendarEntry(user_id="u1", date=FIRST, entry_type="x"))
    assert cal.get_due_entries("u2", FIRST + timedelta(days=5)) == []


# ── Entry → retrospective type mapping (§7.3) ────────────────────────────────
def test_map_anniversary_to_retrospective_type():
    entry = CalendarEntry(user_id="u1", date=FIRST,
                          entry_type=CalendarEntryType.ANNIVERSARY_1YEAR.value)
    assert lc.map_entry_to_retrospective_type(entry) == RetrospectiveType.ONE_YEAR_AGO.value
