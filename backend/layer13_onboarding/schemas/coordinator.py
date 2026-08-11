"""Coordinator directive schemas (architecture doc §7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.layer13_onboarding.schemas.cold_start_state import InitialState
from backend.layer13_onboarding.schemas.elicitation import ElicitationItem
from backend.layer13_onboarding.schemas.graduation import GraduationHandoff


@dataclass
class SessionStartDirectives:
    cold_start_active: bool
    personality_drift_gate: float
    proactivity_mode: str
    longitudinal_mode: str
    max_elicitation_this_session: int
    active_features: list = field(default_factory=list)


@dataclass
class MessageDirectives:
    pending_elicitation_question: Optional[ElicitationItem] = None
    feature_introduction_events: list = field(default_factory=list)
    updated_state: Optional[InitialState] = None


@dataclass
class SessionEndResult:
    graduated: bool
    handoff: Optional[GraduationHandoff] = None
    criteria_met: list = field(default_factory=list)
    criteria_remaining: list = field(default_factory=list)
