"""SC-2 RelationshipState types (architecture doc §4)."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import MemoryReferencePolicy, RelationshipStage, SelfDisclosureDepth


@dataclass
class SessionSummary:
    """Per-session signals consumed by the tie-strength delta (architecture doc §4.3)."""

    had_vulnerability_moment: bool = False
    explicit_trust_signals_count: int = 0
    total_messages: int = 0
    max_emotional_intensity: float = 0.0
    repair_occurred: bool = False


@dataclass
class RelationshipState:
    """Multi-dimensional relationship model (architecture doc §4.2)."""

    # Tie strength
    tie_strength: float = 0.0
    relationship_age_days: int = 0
    total_sessions: int = 0
    total_messages_exchanged: int = 0

    # Stage
    stage: str = RelationshipStage.NEW.value

    # Intimacy model
    emotional_disclosure_depth: float = 0.0
    personal_topic_exposure: float = 0.0
    vulnerability_moments: int = 0
    reciprocity_score: float = 0.0

    # Trust
    trust_score: float = 0.0
    repair_events: int = 0
    explicit_trust_signals: int = 0

    # Communication-style calibration
    formality_preference: float = 0.5
    response_length_preference: float = 0.5
    question_tolerance: float = 0.5
    unsolicited_advice_tolerance: float = 0.5

    # Behavioral gates derived from stage (§4.4)
    self_disclosure_ceiling: str = SelfDisclosureDepth.SURFACE.value
    memory_reference_policy: str = MemoryReferencePolicy.NONE.value
    follow_up_question_ceiling: int = 1
    direct_noticing_allowed: bool = False
