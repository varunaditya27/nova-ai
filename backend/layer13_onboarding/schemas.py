"""Schemas for Layer 13 — Onboarding & Cold Start Architecture (architecture doc §4-§7).

Pure-stdlib dataclasses + str-enums. Layer 13 is the temporary Cold Start Engine overlay:
Progressive Elicitation (SC-1), Cold Start Handling (SC-2), and Feature Introduction Pacing
(SC-3), coordinated by the ColdStartEngine, which self-terminates on graduation. Population
defaults here are the statistically-grounded starting points the doc specifies for unknown
users; `make_initial_state()` (context_constructor) is the factory because dataclasses with
mutable/nested defaults must not be shared across users.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


# ── SC-1 Progressive Elicitation (§4.2) ───────────────────────────────────────
ELICITATION_CATEGORIES = (
    "identity", "life_context", "communication_pref", "goals",
    "relationships", "values", "emotional_style", "reason_for_use",
)


@dataclass
class ElicitationItem:
    category: str
    inference_target: str
    priority: int                                  # 1=critical, 2=important, 3=nice-to-have
    question: Optional[str] = None                 # None => inferred-only, never asked
    prerequisite_item_ids: list = field(default_factory=list)
    can_infer_without_asking: bool = False
    natural_triggers: list = field(default_factory=list)
    status: str = "waiting"                         # waiting|surfaced|answered|inferred|expired
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    surfaced_at_session: Optional[int] = None
    answered_at_session: Optional[int] = None
    inferred_value: Optional[str] = None


# ── SC-1 Passive signal bundle + its 8 component signals (§4.5) ────────────────
@dataclass
class VocabularyRegister:
    avg_word_length: float = 0.0
    avg_sentence_length: float = 0.0
    uses_emoji: bool = False
    formality_delta: int = 0
    message_length: int = 0


@dataclass
class EmotionalExpressionStyle:
    style: str = "indirect"                         # direct|indirect
    confidence: float = 0.2


@dataclass
class TopicApproach:
    hedges_views: bool = False
    seeks_opinions: bool = False
    seeks_facts: bool = False
    context_builder: bool = False


@dataclass
class DisclosureComfort:
    density: float = 0.0
    level: str = "low"                              # low|medium|high


@dataclass
class NamedPersonSignal:
    name: str
    relationship_type: Optional[str] = None
    confidence: float = 0.0


@dataclass
class LifeContextSignals:
    life_phase_signal: Optional[str] = None         # student|working|None
    life_phase_confidence: float = 0.0


@dataclass
class UrgencySignal:
    level: str = "medium"                           # high|medium|low


@dataclass
class CommunicationStyleUpdate:
    avg_user_message_length: float = 0.0
    verbosity_preference: str = "medium"            # concise|medium|verbose
    sample_count: int = 0


@dataclass
class PassiveSignalBundle:
    vocabulary_register: VocabularyRegister = field(default_factory=VocabularyRegister)
    emotional_expression_style: EmotionalExpressionStyle = field(default_factory=EmotionalExpressionStyle)
    topic_approach: TopicApproach = field(default_factory=TopicApproach)
    self_disclosure_comfort: DisclosureComfort = field(default_factory=DisclosureComfort)
    temporal_pattern: Optional[str] = None
    named_entities: list = field(default_factory=list)
    life_context_signals: LifeContextSignals = field(default_factory=LifeContextSignals)
    urgency_signals: UrgencySignal = field(default_factory=UrgencySignal)
    communication_style: CommunicationStyleUpdate = field(default_factory=CommunicationStyleUpdate)


# ── SC-2 Cold Start Handling (§5.1) ───────────────────────────────────────────
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
    named_relationships: list = field(default_factory=list)

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
    relationship_stage_advance_gate: float = 0.50
    relationship_stage_advance_gate_cold_start: float = 0.75
    max_elicitation_per_session: int = 1
    elicitation_embargo_on_emotional_intensity: float = 0.60
    safety_layer_active: bool = True               # never gated, under any condition


# ── SC-2 Graduation (§5.4) ────────────────────────────────────────────────────
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


# ── SC-3 Feature Introduction Pacing (§6.2) ───────────────────────────────────
class IntroductionStyle(str, Enum):
    SILENT = "silent"
    SOFT_OFFER = "soft_offer"
    EXPLAINED = "explained"


@dataclass
class FeatureTechnicalPrereqs:
    minimum_sessions: int = 0
    minimum_exchanges: int = 0
    required_context_fields: list = field(default_factory=list)
    cold_start_must_be_complete: bool = False


@dataclass
class FeatureRelationalPrereqs:
    user_has_shared_personally: bool = False
    positive_engagement_sessions: int = 0
    no_negative_surprise_events: bool = False
    user_has_returned_voluntarily: int = 0


@dataclass
class FeatureReadinessProfile:
    feature_id: str
    layer: int
    feature_name: str
    technical_prereqs: FeatureTechnicalPrereqs
    relational_prereqs: FeatureRelationalPrereqs
    introduction_style: str
    trigger_condition: str
    intro_message: Optional[str] = None


@dataclass
class FeatureIntroductionEvent:
    feature_id: str
    introduction_style: str
    intro_message: Optional[str]
    triggered_at_session: int


# ── Coordinator directives (§7) ───────────────────────────────────────────────
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
