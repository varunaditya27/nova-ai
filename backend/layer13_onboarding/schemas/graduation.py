"""SC-2 Graduation schemas (architecture doc §5.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from backend.layer13_onboarding.schemas.cold_start_state import InitialState


@dataclass
class GraduationCriterion:
    name: str
    check: Callable[[Any], bool]
    description: str


@dataclass
class GraduationResult:
    should_graduate: bool
    criteria_met: list = field(default_factory=list)
    criteria_failed: list = field(default_factory=list)
    nice_to_have_met: list = field(default_factory=list)


@dataclass
class GraduationHandoff:
    graduated_at: datetime
    session_count_at_graduation: int
    exchange_count_at_graduation: int
    final_initial_state: InitialState
