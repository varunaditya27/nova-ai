"""SC-2 Social Event (architecture doc §4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .enums import Recency, SocialEventType


@dataclass
class SocialEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    person_id: str = ""
    event_type: str = SocialEventType.CONFLICT_ONSET.value

    summary: str = ""                       # neutral extracted description (never raw text)
    user_perspective: str = ""

    event_valence: float = 0.0
    emotional_intensity: float = 0.0

    event_timestamp: Optional[datetime] = None
    reported_timestamp: Optional[datetime] = None
    recency: str = Recency.CURRENT.value

    is_resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    resolution_summary: Optional[str] = None

    extraction_confidence: float = 0.0

    related_event_ids: list[str] = field(default_factory=list)
    pattern_id: Optional[str] = None
