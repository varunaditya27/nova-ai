"""Life calendar job — Layer-10 SC-5 scheduler + SC-4 retrospective generation.

Runs daily. Lazily registers the standard relationship milestones (day 30/100/365) for a user's
first run and life-event anniversaries (1/2/3 years) for any real, persisted `LifeEvent` not yet
registered, rebuilds an in-memory LifeCalendar from persisted entries, fires anything due, and for
each newly fired entry that maps to a retrospective type (SC-5 -> SC-4, architecture doc §7.3),
generates and persists a real, grounded retrospective and hands it off to Layer 6's outreach queue
via the real on_retrospective_ready intake contract. The Nova-relationship's own 1-year milestone
additionally generates and persists a real `YearInReview` (§6.4) and re-registers itself for the
following year, closing the "no annual trigger decided" gap -- the milestone firing IS the trigger.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("nova.jobs")

_YEARLY_MILESTONE_TYPE = "nova_relationship_day365"   # CalendarEntryType.NOVA_RELATIONSHIP_DAY365


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from infra.db.goal_store import PostgresGoalStore
    from infra.db.proactive_store import PostgresProactiveQueue
    from backend.layer10_longitudinal.life_calendar import (
        LifeCalendar, map_entry_to_retrospective_type,
    )
    from backend.layer10_longitudinal.retrospective import (
        generate_retrospective, generate_year_in_review,
    )
    from backend.layer10_longitudinal.schemas import CalendarEntry, Layer6Action
    from backend.layer7_goals.schemas import GoalStatus
    from backend.layer6_proactivity.intake import on_calendar_entry_due, on_retrospective_ready
    from background._adapters import emotional_records, episodic_records

    uid = app_state.default_user_id
    tz_offset = app_state.config.get("system", {}).get("timezone_offset_hours", 0.0)
    now = datetime.now(timezone.utc)
    today = (now).astimezone(timezone.utc).date()

    long_store = PostgresLongitudinalStore(app_state.session_factory, uid)
    rel_store = PostgresRelationshipStore(app_state.session_factory, uid)

    calendar = LifeCalendar()
    calendar.entries = long_store.calendar_entries()
    if not calendar.entries:
        first_session = rel_store.first_session_date()
        if first_session is None:
            return {"entries": 0, "reason": "no relationship state yet"}
        calendar.register_new_user(uid, first_session)

    # register_life_event (real, previously uncalled -- SC-5) registers 1/2/3-year anniversary
    # entries for a life event exactly once; skip any life event already represented.
    registered_event_ids = {e.associated_id for e in calendar.entries if e.associated_id}
    for event in long_store.life_events():
        if event.event_id not in registered_event_ids:
            calendar.register_life_event(event)

    due = calendar.check_and_fire_due_entries(uid, today)

    year_in_review_generated = 0
    for entry in list(due):
        if entry.entry_type == _YEARLY_MILESTONE_TYPE:
            # Re-register the next year's milestone so this is a genuinely annual trigger, not
            # a one-time day-365 event -- each fire schedules its own successor.
            calendar.add_entry(CalendarEntry(
                user_id=uid, date=entry.date + timedelta(days=365),
                entry_type=_YEARLY_MILESTONE_TYPE, title="Another year with Nova",
                priority=entry.priority, is_recurring=True,
                layer6_action=Layer6Action(action_type="queue_for_next_session",
                                           urgency="within_week")))

    long_store.save_calendar_entries(calendar.entries)
    if not due:
        return {"entries": len(calendar.entries), "fired": 0, "retrospectives": 0}

    memory_store = PostgresMemoryStore(app_state.session_factory)
    goals = PostgresGoalStore(app_state.session_factory, uid).load_by_status(
        [s.value for s in GoalStatus])
    eps = episodic_records(memory_store, uid, tz_offset)
    emos = emotional_records(memory_store, uid, tz_offset)
    weekly_summaries = long_store.summaries(period="weekly")
    narrative_arc = long_store.load_narrative_arc()

    from backend.layer10_longitudinal.progress_tracker import compute_progress_snapshot
    progress = compute_progress_snapshot(uid, today, emos, [], goals, eps)

    client = (getattr(app_state, "llm_clients", None) or {}).get("system1")
    queue = PostgresProactiveQueue(app_state.session_factory, uid)
    generated, milestones, year_reviews = 0, 0, 0
    for entry in due:
        retro_type = map_entry_to_retrospective_type(entry)
        if retro_type is not None:
            reference_date = entry.date  # the anniversary's own date is the look-back anchor
            packet = generate_retrospective(
                retro_type, reference_date, today, narrative_arc, weekly_summaries, progress,
                goals, eps, llm_fn=(client.complete if client is not None else None))
            long_store.save_retrospective(packet)
            item = on_retrospective_ready(packet, now=now)
            item.item_id = f"retro-{packet.packet_id}"
            queue.upsert(item)
            generated += 1
        else:
            # A pure relationship-milestone entry (e.g. "Day 30 with Nova") -- a celebration
            # nudge, not a look-back, so it goes straight to Layer 6 without a retrospective.
            item = on_calendar_entry_due(entry, now=now)
            item.item_id = f"calendar-{entry.entry_id}"
            queue.upsert(item)
            milestones += 1

        # The Nova-relationship's own annual milestone is also the decided annual trigger for
        # SC-4's YearInReview (architecture doc §6.4) -- richer than a look-back retrospective
        # (full-year goal/chapter/emotional-arc aggregation), generated in addition to, not
        # instead of, the celebration nudge above.
        if entry.entry_type == _YEARLY_MILESTONE_TYPE:
            year = generate_year_in_review(
                uid, entry.date - timedelta(days=365), entry.date, narrative_arc,
                weekly_summaries, progress, goals,
                llm_fn=(client.complete if client is not None else None))
            long_store.save_year_in_review(year)
            year_reviews += 1

    logger.info("life calendar: entries=%d fired=%d retrospectives=%d milestones=%d "
                "year_reviews=%d", len(calendar.entries), len(due), generated, milestones,
                year_reviews)
    return {"entries": len(calendar.entries), "fired": len(due), "retrospectives": generated,
            "milestones": milestones, "year_reviews": year_reviews}
