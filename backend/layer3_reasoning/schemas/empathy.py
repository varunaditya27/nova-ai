"""SC-5 Empathy Hypothesis Generator types (architecture doc §7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PrimaryNeed(str, Enum):
    """What the user most needs from Nova (architecture doc §7.2)."""

    TO_BE_HEARD = "to_be_heard"
    TO_BE_VALIDATED = "to_be_validated"
    TO_CELEBRATE = "to_celebrate"
    TO_PROBLEM_SOLVE = "to_problem_solve"
    TO_THINK_ALOUD = "to_think_aloud"
    TO_DECIDE = "to_decide"
    SPACE_TO_SIT_WITH_IT = "space_to_sit_with_it"
    INFORMATION = "information"
    DISTRACTION = "distraction"
    CRISIS_SUPPORT = "crisis_support"


class ResponsePosture(str, Enum):
    """The governing response stance (architecture doc §7.2)."""

    VALIDATE_THEN_HOLD = "validate_then_hold"
    VALIDATE_THEN_SOLVE = "validate_then_solve"
    CELEBRATE = "celebrate"
    CO_THINK = "co_think"
    INFORM_WITH_WARMTH = "inform_with_warmth"
    GENTLE_REDIRECT = "gentle_redirect"
    LISTEN_ONLY = "listen_only"
    CRISIS_PROTOCOL = "crisis_protocol"


class DisclosureDepth(str, Enum):
    """How much relational depth the response may assume (architecture doc §7.2)."""

    SURFACE = "surface"
    MODERATE = "moderate"
    DEEP = "deep"


@dataclass
class EmpathyHypothesis:
    """Auditable internal reasoning bridging classification and generation (§7.2)."""

    primary_feeling: str = ""
    feeling_basis: str = ""
    secondary_feeling: Optional[str] = None
    primary_need: str = PrimaryNeed.INFORMATION.value
    secondary_need: Optional[str] = None
    response_posture: str = ResponsePosture.INFORM_WITH_WARMTH.value
    advice_withheld: bool = False
    advice_withheld_reason: Optional[str] = None
    apply_mismatch_posture: bool = False
    mismatch_posture: Optional[str] = None
    disclosure_depth_allowed: str = DisclosureDepth.SURFACE.value
    is_crisis: bool = False
    skip_emotional_refinement: bool = False
    generated_at: datetime = field(default_factory=datetime.utcnow)
    basis_summary: str = ""
