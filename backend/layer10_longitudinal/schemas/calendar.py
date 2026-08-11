"""SC-5 Life Calendar schemas (architecture doc §7.2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class CalendarEntryType(str, Enum):
    WEEKLY_SUMMARY_DUE = "weekly_summary_due"
    MONTHLY_NARRATIVE_UPDATE = "monthly_narrative_update"
    QUARTERLY_GROWTH_REVIEW = "quarterly_growth_review"
    ANNIVERSARY_1YEAR = "anniversary_1year"
    ANNIVERSARY_6MONTH = "anniversary_6month"
    ANNIVERSARY_3MONTH = "anniversary_3month"
    ANNIVERSARY_1MONTH = "anniversary_1month"
    GOAL_TARGET_DATE = "goal_target_date"
    GOAL_ANNIVERSARY = "goal_anniversary"
    GOAL_STALENESS_CHECK = "goal_staleness_check"
    LIFE_EVENT_ANNIVERSARY = "life_event_anniversary"
    CHAPTER_BOUNDARY_DETECTED = "chapter_boundary_detected"
    NOVA_RELATIONSHIP_DAY30 = "nova_relationship_day30"
    NOVA_RELATIONSHIP_DAY100 = "nova_relationship_day100"
    NOVA_RELATIONSHIP_DAY365 = "nova_relationship_day365"
    PENDING_THREAD_DUE = "pending_thread_due"
    PATTERN_DETECTED = "pattern_detected"


@dataclass
class Layer6Action:
    action_type: str = "background_update_only"   # surface_retrospective|generate_and_surface|
                                                  # queue_for_next_session|surface_if_session_opens
    urgency: str = "opportunistic"                # immediate|within_24h|within_week|opportunistic
    retrospective_packet_id: Optional[str] = None
    message_suggestion: Optional[str] = None


@dataclass
class CalendarEntry:
    user_id: str
    date: date
    entry_type: str
    title: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    associated_id: Optional[str] = None
    priority: float = 0.5
    is_recurring: bool = False
    layer6_action: Optional[Layer6Action] = None
    lookback_days: int = 0
    has_fired: bool = False
    fired_at: Optional[datetime] = None
