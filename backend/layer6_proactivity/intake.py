"""Layer 6 intake contracts — how items enter the queue (architecture doc §9).

Each upstream layer has a constructor that turns its native signal into a ``ProactiveItem``
with the correct type, priority, timing windows, and grounding references. SC-1 then owns
the item's lifecycle.

Reconciliation: §9.1 references a generic ``PendingThread`` with ``event_date`` and
``emotional_anticipation_score``; the implemented Layer 1 type is ``NarrativeThread`` with
``follow_up_due_at`` and ``emotional_weight``. We map those fields directly. §9.4 references
the not-yet-built Layer 7 ``Goal``/``Milestone``; the contract here takes the goal fields as
plain arguments so Layer 6 does not depend on Layer 7's internals.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from backend.layer1_input.schemas import NarrativeThread
from backend.layer5_relationship.schemas import CoachingOpportunity
from backend.layer6_proactivity.queue_manager import BASE_PRIORITY_BY_TYPE
from backend.layer6_proactivity.schemas import ProactiveItem, ProactiveItemType


def on_thread_due(thread: NarrativeThread, now: Optional[datetime] = None) -> ProactiveItem:
    """Create a thread follow-up / upcoming-date item from a Layer 1 thread (§9.1)."""
    now = now or datetime.utcnow()
    event_date = thread.follow_up_due_at
    item_type = (ProactiveItemType.THREAD_FOLLOW_UP.value if event_date < now
                 else ProactiveItemType.UPCOMING_DATE_REMINDER.value)
    earliest = event_date + timedelta(hours=18)   # wait 18h after the event
    return ProactiveItem(
        item_type=item_type,
        source_layer="layer1",
        content_basis=thread.summary,
        content_basis_valence=thread.emotional_weight,
        source_memory_ids=[str(thread.thread_id)],
        base_priority=BASE_PRIORITY_BY_TYPE[ProactiveItemType.THREAD_FOLLOW_UP.value],
        earliest_send_time=earliest,
        optimal_send_window=(earliest, event_date + timedelta(days=3)),
        expiry_time=event_date + timedelta(days=7),
        created_at=now,
    )


def on_post_distress_gap(
    session_summary: str,
    episode_id: str,
    end_valence: float,
    gap_days: int,
    now: Optional[datetime] = None,
) -> Optional[ProactiveItem]:
    """Create an emotional check-in after a high-distress session + gap (§9.2)."""
    now = now or datetime.utcnow()
    if gap_days < 3 or end_valence >= -0.6:
        return None
    return ProactiveItem(
        item_type=ProactiveItemType.EMOTIONAL_CHECK_IN.value,
        source_layer="layer2",
        content_basis=session_summary,
        source_memory_ids=[episode_id],
        base_priority=0.85,
        earliest_send_time=now + timedelta(hours=6),
        optimal_send_window=(now + timedelta(hours=6), now + timedelta(days=5)),
        expiry_time=now + timedelta(days=14),
        created_at=now,
    )


def on_deferred_coaching(
    opportunity: CoachingOpportunity,
    person_display_name: Optional[str] = None,
    now: Optional[datetime] = None,
) -> ProactiveItem:
    """Create a social-pattern coaching item from a deferred Layer 5 opportunity (§9.3)."""
    now = now or datetime.utcnow()
    event_ids = []
    if opportunity.triggering_event is not None:
        event_ids = [opportunity.triggering_event.event_id]
    return ProactiveItem(
        item_type=ProactiveItemType.SOCIAL_PATTERN_COACHING.value,
        source_layer="layer5",
        content_basis=opportunity.observation_text,
        source_event_ids=event_ids,
        person_id=opportunity.triggering_person,
        person_display_name=person_display_name,
        base_priority=0.55,
        earliest_send_time=now + timedelta(days=2),   # always delay by 2+ days
        optimal_send_window=(now + timedelta(days=2), now + timedelta(days=14)),
        expiry_time=now + timedelta(days=30),
        created_at=now,
    )


def on_behavioral_pattern(pattern, now: Optional[datetime] = None) -> ProactiveItem:
    """Create a gentle pattern-surfacing item from a Layer-10 SC-3 BehavioralPattern."""
    now = now or datetime.utcnow()
    return ProactiveItem(
        item_type=ProactiveItemType.BEHAVIORAL_PATTERN_SURFACING.value,
        source_layer="layer10",
        content_basis=pattern.description,
        source_memory_ids=[],
        base_priority=BASE_PRIORITY_BY_TYPE[ProactiveItemType.BEHAVIORAL_PATTERN_SURFACING.value],
        earliest_send_time=now + timedelta(days=1),
        optimal_send_window=(now + timedelta(days=1), now + timedelta(days=10)),
        expiry_time=now + timedelta(days=21),
        created_at=now,
    )


def on_retrospective_ready(retrospective, now: Optional[datetime] = None) -> ProactiveItem:
    """Create a reflective item from a Layer-10 SC-4 RetrospectivePacket that just fired (§9)."""
    now = now or datetime.utcnow()
    window_days = getattr(retrospective, "surfacing_window_days", 7)
    return ProactiveItem(
        item_type=ProactiveItemType.RETROSPECTIVE_REFLECTION.value,
        source_layer="layer10",
        content_basis=retrospective.headline or retrospective.narrative_reflection,
        source_memory_ids=list(retrospective.backing_episode_ids or []),
        base_priority=BASE_PRIORITY_BY_TYPE[ProactiveItemType.RETROSPECTIVE_REFLECTION.value]
        + (retrospective.surfacing_priority - 0.5) * 0.2,
        earliest_send_time=now,
        optimal_send_window=(now, now + timedelta(days=window_days)),
        expiry_time=now + timedelta(days=window_days * 2),
        created_at=now,
    )


def on_calendar_entry_due(entry, now: Optional[datetime] = None) -> ProactiveItem:
    """Create an upcoming-date item from a fired Layer-10 SC-5 CalendarEntry that does NOT map to
    a retrospective (e.g. a Nova-relationship-day milestone) -- a pure celebration nudge, not a
    look-back. Entries that DO map to a retrospective type go through on_retrospective_ready
    instead, once SC-4 has generated the real grounded reflection."""
    now = now or datetime.utcnow()
    urgency = getattr(entry.layer6_action, "urgency", "opportunistic") if entry.layer6_action else "opportunistic"
    delay = timedelta(hours=24) if urgency == "within_24h" else timedelta(days=1)
    window_days = 3 if urgency == "within_week" else 7
    return ProactiveItem(
        item_type=ProactiveItemType.UPCOMING_DATE_REMINDER.value,
        source_layer="layer10",
        content_basis=entry.title,
        base_priority=BASE_PRIORITY_BY_TYPE[ProactiveItemType.UPCOMING_DATE_REMINDER.value],
        earliest_send_time=now,
        optimal_send_window=(now, now + delay),
        expiry_time=now + timedelta(days=window_days),
        created_at=now,
    )


def on_goal_milestone_approaching(
    goal_id: str,
    goal_title: str,
    milestone_description: str,
    due_date: datetime,
    now: Optional[datetime] = None,
) -> ProactiveItem:
    """Create a goal check-in when a milestone date is within 72h (§9.4)."""
    now = now or datetime.utcnow()
    return ProactiveItem(
        item_type=ProactiveItemType.GOAL_CHECK_IN.value,
        source_layer="layer7",
        content_basis=f"Goal: {goal_title} | Milestone: {milestone_description}",
        source_goal_id=goal_id,
        base_priority=0.72,
        earliest_send_time=due_date - timedelta(days=1),
        optimal_send_window=(due_date - timedelta(days=1), due_date + timedelta(days=2)),
        expiry_time=due_date + timedelta(days=5),
        created_at=now,
    )
