"""SC-3 Social Pattern (architecture doc §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .enums import PatternScope, SocialPatternType


@dataclass
class SocialPattern:
    pattern_id: str = field(default_factory=lambda: str(uuid4()))
    pattern_type: str = SocialPatternType.RECURRING_CONFLICT_TOPIC.value

    scope: str = PatternScope.INTRA_RELATIONSHIP.value
    person_ids_involved: list[str] = field(default_factory=list)

    supporting_event_ids: list[str] = field(default_factory=list)
    event_count: int = 0
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    observation_span_days: int = 0

    plain_language_description: str = ""
    coaching_hook: str = ""

    pattern_confidence: float = 0.0
    pattern_strength: float = 0.0

    is_active: bool = True
    last_activation: Optional[datetime] = None
    has_been_surfaced: bool = False
    surface_count: int = 0
    user_acknowledged: bool = False
