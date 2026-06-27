"""Schemas for Layer 2 — Cognition & Memory.

The complete data contract for the Memory Arbiter and every sub-component, per
``docs/layer-2-architecture.md``. Pure-stdlib (`dataclasses` + `enum`); no ORM/pydantic.

Five memory types (storage group): Short-Term buffer, Episodic, Semantic, Identity, and the
User World Model. Processing/state types: recall scoring, audit trail, narrative chains, and
the ``MemoryPacket`` contract handed to downstream layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Literal, Optional, Union
from uuid import UUID, uuid4


# ────────────────────────────────────────────────────────────────────────────
# Enumerations
# ────────────────────────────────────────────────────────────────────────────
class ConversationMode(str, Enum):
    """Layer 3's canonical conversation-mode taxonomy (shared across layers).

    The Layer 2 context gate (§8.5) keys on these. Reconciled from the doc's older
    ``casual_small_talk`` / ``crisis_detected`` spellings and the missing ``celebration``.
    """

    CRISIS = "crisis"
    EMOTIONAL_SUPPORT = "emotional_support"
    CELEBRATION = "celebration"
    TECHNICAL_DISCUSSION = "technical_discussion"
    GOAL_PLANNING = "goal_planning"
    SOCIAL_COACHING = "social_coaching"
    LIFE_REVIEW = "life_review"
    CASUAL = "casual"


class ImportanceCategory(str, Enum):
    """Episodic importance categories (§4.3)."""

    LIFE_EVENT_MAJOR = "life_event_major"
    LIFE_EVENT_MINOR = "life_event_minor"
    EMOTIONAL_PEAK = "emotional_peak"
    GOAL_STATED = "goal_stated"
    CONFLICT_INTERPERSONAL = "conflict_interpersonal"
    INSIGHT_EXPRESSED = "insight_expressed"
    RECURRING_STRUGGLE = "recurring_struggle"
    RELATIONSHIP_UPDATE = "relationship_update"
    PREFERENCE_REVEALED = "preference_revealed"
    FACTUAL_DISCLOSURE = "factual_disclosure"
    CASUAL_EXCHANGE = "casual_exchange"
    TASK_REQUEST = "task_request"


# Base importance per category (§4.3 table).
BASE_IMPORTANCE: dict[ImportanceCategory, float] = {
    ImportanceCategory.LIFE_EVENT_MAJOR: 0.95,
    ImportanceCategory.LIFE_EVENT_MINOR: 0.80,
    ImportanceCategory.EMOTIONAL_PEAK: 0.75,
    ImportanceCategory.GOAL_STATED: 0.70,
    ImportanceCategory.CONFLICT_INTERPERSONAL: 0.72,
    ImportanceCategory.INSIGHT_EXPRESSED: 0.65,
    ImportanceCategory.RECURRING_STRUGGLE: 0.68,
    ImportanceCategory.RELATIONSHIP_UPDATE: 0.60,
    ImportanceCategory.PREFERENCE_REVEALED: 0.45,
    ImportanceCategory.FACTUAL_DISCLOSURE: 0.40,
    ImportanceCategory.CASUAL_EXCHANGE: 0.15,
    ImportanceCategory.TASK_REQUEST: 0.10,
}


class SemanticMemoryType(str, Enum):
    PREFERENCE = "preference"
    COMMUNICATION_STYLE = "communication_style"
    EMOTIONAL_PATTERN = "emotional_pattern"
    BEHAVIORAL_TENDENCY = "behavioral_tendency"
    FACTUAL_STABLE = "factual_stable"
    RELATIONSHIP_MODEL = "relationship_model"
    WORLDVIEW = "worldview"
    TRIGGER_PATTERN = "trigger_pattern"
    COPING_MECHANISM = "coping_mechanism"


class IdentityCategory(str, Enum):
    CORE_VALUE = "core_value"
    PERSONALITY_TRAIT = "personality_trait"
    OPINION = "opinion"
    BEHAVIORAL_POLICY = "behavioral_policy"
    SELF_KNOWLEDGE = "self_knowledge"
    RELATIONAL_STANCE = "relational_stance"
    AESTHETIC_PREFERENCE = "aesthetic_preference"


class AuditEventType(str, Enum):
    MEMORY_CREATED = "memory_created"
    MEMORY_RECALLED = "memory_recalled"
    MEMORY_REINFORCED = "memory_reinforced"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_ARCHIVED = "memory_archived"
    MEMORY_DELETED_BY_DECAY = "memory_deleted_by_decay"
    MEMORY_DELETED_BY_USER = "memory_deleted_by_user"
    MEMORY_CONSOLIDATED = "memory_consolidated"
    SEMANTIC_MEMORY_CREATED = "semantic_memory_created"
    SEMANTIC_MEMORY_DEPRECATED = "semantic_memory_deprecated"
    IDENTITY_BELIEF_UPDATED = "identity_belief_updated"
    UWM_UPDATED = "uwm_updated"
    UWM_FIELD_UPDATED = "uwm_field_updated"
    RECALL_ATTEMPTED_NO_RESULT = "recall_attempted_no_result"
    CONTEXT_GATE_SUPPRESSED_RECALL = "context_gate_suppressed_recall"


class NarrativeLinkType(str, Enum):
    CONTINUATION = "continuation"
    ESCALATION = "escalation"
    RESOLUTION = "resolution"
    RELAPSE = "relapse"
    REFRAMING = "reframing"
    NEW_DEVELOPMENT = "new_development"


class ChainStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    STALLED = "stalled"
    ARCHIVED = "archived"


# ────────────────────────────────────────────────────────────────────────────
# Emotion (shared with Layer 3)
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class EmotionVector:
    """Valence/arousal emotional state (§4.2). Defined here as Layer 3 is not yet built."""

    valence: float = 0.0       # –1 (negative) … +1 (positive)
    arousal: float = 0.0       # 0 (calm) … 1 (activated)
    dominant_label: str = "neutral"


# ────────────────────────────────────────────────────────────────────────────
# SC-1 Short-Term Memory Buffer
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class ConversationTurn:
    turn_id: UUID = field(default_factory=uuid4)
    role: Literal["user", "assistant"] = "user"
    content: str = ""
    timestamp: Optional[datetime] = None
    word_count: int = 0
    emotional_annotation: Optional[EmotionVector] = None
    intent_label: Optional[str] = None
    importance_flag: bool = False


@dataclass
class ShortTermMemoryBuffer:
    session_id: UUID
    user_id: UUID
    turns: list[ConversationTurn] = field(default_factory=list)
    max_turns: int = 40
    total_chars: int = 0
    char_limit: int = 12000


# ────────────────────────────────────────────────────────────────────────────
# SC-2 Episodic Memory
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class RecallEvent:
    recalled_at: datetime
    trigger_query: str = ""
    score_at_recall: float = 0.0
    context_mode: str = ""
    was_used_in_response: bool = False


@dataclass
class EpisodicMemory:
    # Identity
    memory_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    session_id: Optional[UUID] = None

    # Content
    summary: str = ""
    embedding: list[float] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    entity_refs: list[str] = field(default_factory=list)
    thread_id: Optional[UUID] = None

    # Temporal
    created_at: Optional[datetime] = None
    session_timestamp: Optional[datetime] = None
    fuzzy_label: str = ""

    # Emotional
    emotion_vector: EmotionVector = field(default_factory=EmotionVector)
    emotional_weight: float = 0.0

    # Memory strength
    importance_score: float = 0.0
    base_importance: float = 0.0
    novelty_score: float = 0.0
    S0: float = 0.0
    S_current: float = 0.0
    decay_rate: float = 0.0
    last_decay_computed_at: Optional[datetime] = None
    reinforcement_count: int = 0
    is_archived: bool = False
    is_deleted: bool = False                       # logical deletion flag (non-destructive)

    # Lineage
    source_turn_ids: list[UUID] = field(default_factory=list)
    consolidated_into: Optional[UUID] = None
    linked_episodes: list[UUID] = field(default_factory=list)
    superseded_by: Optional[UUID] = None

    # Audit
    recall_history: list[RecallEvent] = field(default_factory=list)
    creation_agent: str = ""


# ────────────────────────────────────────────────────────────────────────────
# SC-3 Semantic Memory
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class SemanticMemory:
    memory_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    memory_type: SemanticMemoryType = SemanticMemoryType.FACTUAL_STABLE

    statement: str = ""
    embedding: list[float] = field(default_factory=list)
    confidence: float = 0.5
    supporting_episode_ids: list[UUID] = field(default_factory=list)
    evidence_count: int = 0

    created_at: Optional[datetime] = None
    last_confirmed_at: Optional[datetime] = None
    last_contradicted_at: Optional[datetime] = None
    contradiction_count: int = 0

    decay_rate: float = 0.005
    S_current: float = 1.0
    is_deprecated: bool = False

    retrieval_tags: list[str] = field(default_factory=list)
    relevance_contexts: list[str] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────────
# SC-4 Identity Memory
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class BeliefUpdateEvent:
    updated_at: datetime
    prior_statement: str
    new_statement: str
    triggering_session_id: Optional[UUID] = None
    evidence_strength: float = 0.0
    update_reason: str = ""


@dataclass
class IdentityMemory:
    belief_id: UUID = field(default_factory=uuid4)
    category: IdentityCategory = IdentityCategory.OPINION
    statement: str = ""
    centrality: float = 0.5
    update_threshold: float = 0.625
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    update_history: list[BeliefUpdateEvent] = field(default_factory=list)
    is_immutable: bool = False


@dataclass
class IdentityContradiction:
    belief_id: UUID
    evidence_summary: str
    contradiction_score: float
    session_id: Optional[UUID] = None
    strength: float = 0.0


# ────────────────────────────────────────────────────────────────────────────
# SC-5 User World Model
# ────────────────────────────────────────────────────────────────────────────
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
class SentimentPoint:
    timestamp: datetime
    valence: float
    source_episode_id: Optional[UUID] = None


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
class RelationshipEdge:
    edge_id: UUID = field(default_factory=uuid4)
    person_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    relationship_tier: str = "unclear"
    sentiment_history: list[SentimentPoint] = field(default_factory=list)
    recent_topics: list[str] = field(default_factory=list)
    active_conflicts: list[str] = field(default_factory=list)
    shared_events: list[str] = field(default_factory=list)


@dataclass
class RelationshipGraph:
    user_id: Optional[UUID] = None
    people: list[PersonNode] = field(default_factory=list)
    relationship_edges: list[RelationshipEdge] = field(default_factory=list)
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
class RecurringTheme:
    theme_id: UUID = field(default_factory=uuid4)
    description: str = ""
    first_detected_at: Optional[datetime] = None
    evidence_count: int = 0
    last_occurrence_at: Optional[datetime] = None
    is_improving: Optional[bool] = None
    related_semantic_memory_ids: list[UUID] = field(default_factory=list)


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
    recurring_themes: list[RecurringTheme] = field(default_factory=list)
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


# ────────────────────────────────────────────────────────────────────────────
# SC-8 Audit Trail + Narrative chains
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class AuditEvent:
    event_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    timestamp: Optional[datetime] = None
    event_type: AuditEventType = AuditEventType.MEMORY_CREATED
    memory_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    reason: str = ""
    score_at_event: Optional[float] = None
    prior_value: Optional[str] = None
    new_value: Optional[str] = None
    triggered_by: str = ""
    content_hash: str = ""
    prev_event_hash: str = ""


@dataclass
class ChainedEpisode:
    episode_id: UUID
    position_in_chain: int = 0
    link_type: NarrativeLinkType = NarrativeLinkType.CONTINUATION
    linked_at: Optional[datetime] = None


@dataclass
class NarrativeChain:
    chain_id: UUID = field(default_factory=uuid4)
    theme: str = ""
    episodes: list[ChainedEpisode] = field(default_factory=list)
    status: ChainStatus = ChainStatus.ACTIVE
    first_episode_at: Optional[datetime] = None
    last_episode_at: Optional[datetime] = None
    arc_summary: Optional[str] = None


# ────────────────────────────────────────────────────────────────────────────
# SC-7 FCE outputs
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class EpisodicCluster:
    members: list[EpisodicMemory] = field(default_factory=list)

    @property
    def most_recent_episode(self) -> Optional[EpisodicMemory]:
        dated = [e for e in self.members if e.created_at is not None]
        if dated:
            return max(dated, key=lambda e: e.created_at)
        return self.members[0] if self.members else None


@dataclass
class FCERunReport:
    run_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    run_at: Optional[datetime] = None
    trigger_reason: str = ""
    episodes_evaluated: int = 0
    episodes_deleted: int = 0
    episodes_archived: int = 0
    clusters_detected: int = 0
    semantic_memories_created: int = 0
    episodes_consolidated: int = 0
    new_semantic_summaries: list[str] = field(default_factory=list)
    next_scheduled_run: Optional[datetime] = None


# ────────────────────────────────────────────────────────────────────────────
# SC-6 recall outputs + MemoryPacket contract
# ────────────────────────────────────────────────────────────────────────────
Memory = Union[EpisodicMemory, SemanticMemory]


@dataclass
class ScoredMemory:
    memory: Memory
    recall_score: float = 0.0
    effective_score: float = 0.0
    gate_value: float = 1.0
    components: dict = field(default_factory=dict)
    fuzzy_temporal_label: str = ""


@dataclass
class RecallResult:
    memories: list[ScoredMemory] = field(default_factory=list)   # max 3
    uwm_context: dict = field(default_factory=dict)
    total_candidates_evaluated: int = 0
    retrieval_mode: str = ""
    temperature_used: float = 0.0


@dataclass
class UWMContextSnapshot:
    user_profile_brief: str = ""
    relevant_people: list[PersonNode] = field(default_factory=list)
    active_stressors: list[Stressor] = field(default_factory=list)
    active_situations: list[LifeSituation] = field(default_factory=list)
    psychological_posture: dict = field(default_factory=dict)
    communication_preferences: Optional[CommunicationModel] = None


@dataclass
class MemoryPacket:
    stm_turns: list[ConversationTurn] = field(default_factory=list)
    recalled_memories: list[ScoredMemory] = field(default_factory=list)
    uwm_context: UWMContextSnapshot = field(default_factory=UWMContextSnapshot)
    active_narrative_chains: list[NarrativeChain] = field(default_factory=list)
    retrieval_metadata: RecallResult = field(default_factory=RecallResult)
    fuzzy_label_util: Optional[Callable[[datetime], str]] = None

    # Diagnostic flags (§15 fallback behaviors).
    recall_degraded: bool = False
    uwm_unavailable: bool = False
    cold_start: bool = False
    no_relevant_memories: bool = False
    confabulation_guard: bool = False
