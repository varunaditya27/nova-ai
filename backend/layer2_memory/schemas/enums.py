"""Enumerations for Layer 2 — Cognition & Memory (docs/layer-2-architecture.md)."""

from __future__ import annotations

from enum import Enum


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
