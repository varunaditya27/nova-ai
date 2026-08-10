"""SC-5 User World Model types (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class UserProfile:
    preferred_name: Optional[str] = None
    inferred_age_range: Optional[str] = None
    pronouns: Optional[str] = None
    location_context: Optional[str] = None
    primary_language: str = "en"
    secondary_languages: list[str] = field(default_factory=list)
    current_life_stage: str = "unknown"
    field_of_study_or_work: Optional[str] = None
    institution_or_employer: Optional[str] = None
    current_academic_year: Optional[str] = None
    career_goals_summary: Optional[str] = None
    likely_living_situation: Optional[str] = None


@dataclass
class PersonNode:
    person_id: UUID = field(default_factory=uuid4)
    name: str = ""
    aliases: list[str] = field(default_factory=list)
    relationship_tier: str = "unclear"
    first_mentioned_at: Optional[datetime] = None
    last_mentioned_at: Optional[datetime] = None
    mention_count: int = 0
    inferred_traits: list[str] = field(default_factory=list)
    emotional_significance_to_user: float = 0.0
    current_relationship_valence: float = 0.0
    is_active_in_user_life: bool = True
    source_episode_ids: list[UUID] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class RelationshipGraph:
    user_id: Optional[UUID] = None
    people: list[PersonNode] = field(default_factory=list)
    last_updated: Optional[datetime] = None


@dataclass
class LifeSituation:
    situation_id: UUID = field(default_factory=uuid4)
    description: str = ""
    category: str = "other"
    started_at: Optional[datetime] = None
    estimated_resolution: Optional[datetime] = None
    emotional_weight: float = 0.0
    status: str = "active"
    related_episode_ids: list[UUID] = field(default_factory=list)


@dataclass
class UWMLifeEvent:
    event_id: UUID = field(default_factory=uuid4)
    description: str = ""
    category: str = ""
    occurred_at: Optional[datetime] = None
    emotional_impact: float = 0.0
    is_milestone: bool = False


@dataclass
class Stressor:
    stressor_id: UUID = field(default_factory=uuid4)
    description: str = ""
    intensity: float = 0.0
    duration_days: int = 0
    category: str = ""
    linked_situation_id: Optional[UUID] = None


@dataclass
class LifeContext:
    active_situations: list[LifeSituation] = field(default_factory=list)
    life_events: list[UWMLifeEvent] = field(default_factory=list)
    active_stressors: list[Stressor] = field(default_factory=list)


@dataclass
class TriggerPattern:
    trigger_id: UUID = field(default_factory=uuid4)
    description: str = ""
    response_type: str = ""
    evidence_count: int = 0
    last_observed_at: Optional[datetime] = None


@dataclass
class PsychologicalModel:
    attachment_signals: list[str] = field(default_factory=list)
    emotional_regulation_style: Optional[str] = None
    preferred_support_style: Optional[str] = None
    self_efficacy_signals: list[str] = field(default_factory=list)
    identity_conflict_signals: list[str] = field(default_factory=list)
    known_triggers: list[TriggerPattern] = field(default_factory=list)
    model_confidence: float = 0.0
    last_updated: Optional[datetime] = None
    derived_from_episode_count: int = 0


@dataclass
class CommunicationModel:
    vocabulary_complexity: str = "moderate"
    typical_message_length: str = "moderate"
    uses_slang: bool = False
    uses_humor: bool = False
    humor_style: Optional[str] = None
    code_switches_language: bool = False
    prefers_direct_answers: bool = True
    tolerates_tangents: bool = True
    engages_with_questions: bool = True
    prefers_nova_to_initiate: bool = False
    peak_engagement_bands: list[str] = field(default_factory=list)
    average_session_duration_minutes: float = 0.0
    response_latency_profile: str = "variable"
    last_updated: Optional[datetime] = None
    sessions_used_for_calibration: int = 0


@dataclass
class UserWorldModel:
    user_id: UUID
    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    update_version: int = 0
    profile: UserProfile = field(default_factory=UserProfile)
    relationship_graph: RelationshipGraph = field(default_factory=RelationshipGraph)
    life_context: LifeContext = field(default_factory=LifeContext)
    psychological_model: PsychologicalModel = field(default_factory=PsychologicalModel)
    communication_model: CommunicationModel = field(default_factory=CommunicationModel)
    data_sources: list[str] = field(default_factory=list)
    confidence_by_field: dict[str, float] = field(default_factory=dict)
