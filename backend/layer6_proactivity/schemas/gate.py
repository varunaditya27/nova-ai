"""SC-3 GateDecision + UserTimingContext (architecture doc §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import GateAction


@dataclass
class GateDecision:
    action: str = GateAction.SEND_NOW.value
    reason: str = ""
    retry_after: Optional[datetime] = None
    approved_at: Optional[datetime] = None


@dataclass
class UserTimingContext:
    circadian_band: str = "afternoon"
    user_timezone: str = "UTC"
    minutes_since_last_message: int = 999
    hours_since_last_proactive_message: float = 9999.0
    last_proactive_sent_at: Optional[datetime] = None
    proactive_messages_sent_today: int = 0

    # Emotional state
    bes_trend: str = "stable"
    last_session_crisis_flag: bool = False
    last_session_end_valence: float = 0.0

    # Relationship state
    relationship_stage: str = "developing"
    tie_strength: float = 0.5

    # User preferences
    user_preferences: dict = field(default_factory=dict)
    is_in_quiet_period: bool = False
    quiet_period_end: Optional[datetime] = None

    # Session state
    user_is_currently_active: bool = False
