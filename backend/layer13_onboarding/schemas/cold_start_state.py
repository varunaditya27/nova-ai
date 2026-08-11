"""SC-2 Cold Start Handling schemas (architecture doc §5.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from backend.layer13_onboarding.schemas.passive_signals import NamedPersonSignal


@dataclass
class PersonalityVector:
    warmth: float = 0.75
    verbosity: float = 0.45
    humor: float = 0.35
    formality: float = 0.40
    empathy_bias: float = 0.70
    sarcasm_threshold: float = 0.20
    assertiveness: float = 0.50
    curiosity_expression: float = 0.65
    directness: float = 0.55


@dataclass
class EmotionalBaseline:
    valence: float = 0.15
    arousal: float = 0.20
    engagement_level: float = 0.60


@dataclass
class CommunicationStyleProfile:
    verbosity_preference: str = "medium"
    formality_level: str = "casual"
    emoji_comfort: bool = False
    disclosure_comfort: str = "low"
    emotional_expression_style: str = "indirect"


class RelationshipStage(str, Enum):
    NEW_ACQUAINTANCE = "new_acquaintance"
    FAMILIAR = "familiar"
    TRUSTED = "trusted"


@dataclass
class InitialState:
    user_id: str
    initialized_at: Optional[datetime] = None
    cold_start: bool = True
    cold_start_session_count: int = 0
    cold_start_ends: Optional[datetime] = None
    total_exchange_count: int = 0

    personality_vector: PersonalityVector = field(default_factory=PersonalityVector)
    emotional_baseline: EmotionalBaseline = field(default_factory=EmotionalBaseline)

    episodic_memory: list = field(default_factory=list)
    semantic_memory: list = field(default_factory=list)
    identity_memory: list = field(default_factory=list)

    relationship_stage: str = RelationshipStage.NEW_ACQUAINTANCE.value

    user_handle: Optional[str] = None
    life_phase: Optional[str] = None
    communication_style_profile: Optional[CommunicationStyleProfile] = None
    emotional_baseline_calibrated: bool = False
    primary_topic_areas: list = field(default_factory=list)
    primary_reason: Optional[str] = None
    named_relationships: list[NamedPersonSignal] = field(default_factory=list)

    def apply_update(self, update: "InitialStateUpdate") -> None:
        """Merge a context-builder update into this state (additive / non-destructive)."""
        u = update.updates
        for key in ("user_handle", "life_phase", "communication_style_profile", "primary_reason"):
            if key in u and u[key] is not None:
                setattr(self, key, u[key])
        if "primary_topic_areas" in u:
            self.primary_topic_areas = u["primary_topic_areas"]
        for fact in u.get("new_semantic_facts", []):
            self.semantic_memory.append(fact)
        for person in u.get("new_named_relationships", []):
            self.named_relationships.append(person)
        for dim, value in u.get("personality_vector_drift", {}).items():
            setattr(self.personality_vector, dim, value)


@dataclass
class InitialStateUpdate:
    updates: dict = field(default_factory=dict)


@dataclass
class ColdStartBehaviorConfig:
    suppress_memory_retrieval_failures: bool = True
    personality_drift_gate_multiplier: float = 0.30
    proactivity_mode: str = "observe_only"
    longitudinal_mode: str = "seeded_but_silent"
    max_elicitation_per_session: int = 1
    elicitation_embargo_on_emotional_intensity: float = 0.60
    safety_layer_active: bool = True               # never gated, under any condition
