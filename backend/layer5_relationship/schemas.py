"""Schemas for Layer 5 — Social Intelligence & Coaching.

Layer 5 governs *what Nova understands about the people in the user's life and the
social dynamics between them*. It accumulates social knowledge across sessions and
uses it to offer coaching, perspective, and pattern recognition (architecture doc §1).

Five sub-components produce the read-only ``SocialIntelligencePacket``:

    SC-1 Social Graph Manager            (social_graph.py)
    SC-2 Interpersonal Event Tracker     (event_tracker.py)
    SC-3 Social Pattern Recognizer       (pattern_recognizer.py)
    SC-4 Coaching Opportunity Detector   (coaching_detector.py)
    SC-5 Social Coaching Response Modifier (coaching_modifier.py)
    orchestrator                          (packet_builder.py)

Type reuse (single source of truth): the final response and voice parameters come
from Layer 4; the emotional context comes from Layer 3. Layer 5 owns the richer
``SocialGraph`` / ``SocialNode`` / ``SocialEvent`` / ``SocialPattern`` model described
in the doc — distinct from Layer 2's lighter UWM ``RelationshipGraph`` / ``PersonNode``
snapshot, which Layer 5 *writes to* via ``SocialContextUpdate`` (architecture doc §9, §14).

Pure stdlib (dataclasses + str-Enum) so the entire layer runs and tests offline.
Embedding-dependent steps (entity resolution, conflict-topic clustering) accept an
injected ``similarity_fn`` with a token-overlap default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

# Upstream types (single source of truth).
from backend.layer4_persona.schemas import (  # noqa: F401  (re-exported)
    FinalResponsePacket,
    VoiceParameters,
)


# ════════════════════════════════════════════════════════════════════════════
# SC-1 Social Graph enums
# ════════════════════════════════════════════════════════════════════════════
class RelationshipType(str, Enum):
    """How the user relates to a person in their social world (architecture doc §3.2)."""

    FAMILY_IMMEDIATE = "family_immediate"
    FAMILY_EXTENDED = "family_extended"
    ROMANTIC_PARTNER = "romantic_partner"
    CLOSE_FRIEND = "close_friend"
    FRIEND = "friend"
    ACQUAINTANCE = "acquaintance"
    COLLEAGUE = "colleague"
    MANAGER = "manager"
    MENTOR = "mentor"
    PEER_ACADEMIC = "peer_academic"
    PEER_PROFESSIONAL = "peer_professional"
    AUTHORITY_FIGURE = "authority_figure"
    RIVAL = "rival"
    EX = "ex"
    ONLINE_FRIEND = "online_friend"
    UNKNOWN = "unknown"


class InteractionFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    RARELY = "rarely"
    ESTRANGED = "estranged"
    UNKNOWN = "unknown"


# ════════════════════════════════════════════════════════════════════════════
# SC-2 Event enums
# ════════════════════════════════════════════════════════════════════════════
class SocialEventType(str, Enum):
    """Taxonomy of meaningful social events (architecture doc §4.2)."""

    # Conflict events
    CONFLICT_ONSET = "conflict_onset"
    CONFLICT_ESCALATION = "conflict_escalation"
    CONFLICT_DEESCALATION = "conflict_deescalation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    CONFLICT_DORMANT = "conflict_dormant"

    # Connection events
    RECONNECTION = "reconnection"
    DEEPENING = "deepening"
    DRIFT = "drift"
    RUPTURE = "rupture"
    REPAIR = "repair"

    # Milestone events
    LIFE_MILESTONE_SHARED = "life_milestone_shared"
    ACHIEVEMENT_SHARED = "achievement_shared"
    LOSS_SHARED = "loss_shared"

    # Behavioral events (other person)
    BOUNDARY_VIOLATION = "boundary_violation"
    SUPPORT_RECEIVED = "support_received"
    SUPPORT_WITHHELD = "support_withheld"
    BETRAYAL = "betrayal"
    POSITIVE_SURPRISE = "positive_surprise"

    # User behavior events
    USER_SET_BOUNDARY = "user_set_boundary"
    USER_AVOIDED_CONFLICT = "user_avoided_conflict"
    USER_REACHED_OUT = "user_reached_out"
    USER_WITHDREW = "user_withdrew"


class Recency(str, Enum):
    CURRENT = "current"
    RECENT = "recent"
    PAST = "past"
    DISTANT_PAST = "distant_past"


# ════════════════════════════════════════════════════════════════════════════
# SC-3 Pattern enums
# ════════════════════════════════════════════════════════════════════════════
class SocialPatternType(str, Enum):
    """Recurring social dynamics (architecture doc §5.2)."""

    # Intra-relationship
    RECURRING_CONFLICT_TOPIC = "recurring_conflict_topic"
    RECURRING_SUPPORT_FAILURE = "recurring_support_failure"
    RECURRING_POSITIVE_REINFORCEMENT = "recurring_positive_reinforcement"
    RELATIONSHIP_CYCLING = "relationship_cycling"
    ESCALATING_TENSION = "escalating_tension"
    STABILIZING_RELATIONSHIP = "stabilizing_relationship"

    # Cross-relationship (user behavior)
    CONFLICT_AVOIDANCE_PATTERN = "conflict_avoidance_pattern"
    PEOPLE_PLEASING_PATTERN = "people_pleasing_pattern"
    BOUNDARY_DIFFICULTY_PATTERN = "boundary_difficulty_pattern"
    SOCIAL_WITHDRAWAL_PATTERN = "social_withdrawal_pattern"
    DEPENDENCY_PATTERN = "dependency_pattern"
    HEALTHY_RELATIONSHIP_PATTERN = "healthy_relationship_pattern"

    # Temporal
    NETWORK_SHRINKAGE = "network_shrinkage"
    NETWORK_GROWTH = "network_growth"
    SUPPORT_NETWORK_EROSION = "support_network_erosion"
    INCREASED_SOCIAL_ENGAGEMENT = "increased_social_engagement"


class PatternScope(str, Enum):
    INTRA_RELATIONSHIP = "intra_relationship"
    CROSS_RELATIONSHIP = "cross_relationship"
    TEMPORAL = "temporal"


# ════════════════════════════════════════════════════════════════════════════
# SC-4 Coaching enums
# ════════════════════════════════════════════════════════════════════════════
class CoachingType(str, Enum):
    PATTERN_REFLECTION = "pattern_reflection"
    PERSPECTIVE_OFFER = "perspective_offer"
    RELATIONSHIP_CHECK_IN = "relationship_check_in"
    GENTLE_REFRAME = "gentle_reframe"
    STRENGTH_ACKNOWLEDGMENT = "strength_acknowledgment"
    SUPPORT_NETWORK_NUDGE = "support_network_nudge"
    CONFLICT_NAVIGATION = "conflict_navigation"
    BOUNDARY_SUPPORT = "boundary_support"


class DeliveryMode(str, Enum):
    INLINE = "inline"
    AS_QUESTION = "as_question"
    DEFERRED = "deferred"
    PROACTIVE_FUTURE = "proactive_future"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ════════════════════════════════════════════════════════════════════════════
# §9 UWM social-context enums
# ════════════════════════════════════════════════════════════════════════════
class SupportNetworkHealth(str, Enum):
    ROBUST = "robust"        # 3+ consistent support sources
    ADEQUATE = "adequate"    # 1–2 support sources
    THIN = "thin"            # 1 support source only
    ISOLATED = "isolated"    # no consistent support sources


class SocialEngagementTrend(str, Enum):
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"
    INSUFFICIENT_DATA = "insufficient_data"


# ════════════════════════════════════════════════════════════════════════════
# SC-1 Social Graph dataclasses
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class SocialNode:
    """One person in the user's social world — built only from what the user said (§3.2)."""

    person_id: str = field(default_factory=lambda: str(uuid4()))
    display_name: str = ""
    name_aliases: list[str] = field(default_factory=list)
    relationship_type: str = RelationshipType.UNKNOWN.value
    relationship_subtype: Optional[str] = None

    # Relationship valence
    relationship_valence: float = 0.0       # –1.0 … +1.0
    valence_confidence: float = 0.0
    valence_trend: float = 0.0              # slope; + improving, − worsening

    interaction_frequency: str = InteractionFrequency.UNKNOWN.value
    narrative_stability: float = 0.0

    # Conflict history
    active_conflict: bool = False
    conflict_count: int = 0
    conflict_topics: list[str] = field(default_factory=list)

    # Support role
    is_support_source: bool = False
    support_quality: Optional[float] = None

    first_mentioned: Optional[datetime] = None
    last_mentioned: Optional[datetime] = None
    mention_count: int = 0

    data_source: str = "user_stated"        # never inferred (§13 principle 2)
    confidence: float = 0.0


@dataclass
class SocialEdge:
    """A relationship edge; one endpoint is always the user (architecture doc §3.2)."""

    person_id_a: str = ""
    person_id_b: str = ""
    relationship_type: str = RelationshipType.UNKNOWN.value
    tie_strength: float = 0.0
    tie_strength_trend: float = 0.0
    last_interaction_reported: Optional[datetime] = None
    shared_contexts: list[str] = field(default_factory=list)
    co_mentions: list[str] = field(default_factory=list)


@dataclass
class SocialGraph:
    user_id: str = ""
    nodes: dict = field(default_factory=dict)   # person_id -> SocialNode
    edges: dict = field(default_factory=dict)   # (a, b) -> SocialEdge
    last_updated: Optional[datetime] = None
    version: int = 0


# ════════════════════════════════════════════════════════════════════════════
# SC-2 Social Event
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class SocialEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    person_id: str = ""
    event_type: str = SocialEventType.CONFLICT_ONSET.value

    summary: str = ""                       # neutral extracted description (never raw text)
    user_perspective: str = ""

    event_valence: float = 0.0
    emotional_intensity: float = 0.0

    event_timestamp: Optional[datetime] = None
    reported_timestamp: Optional[datetime] = None
    recency: str = Recency.CURRENT.value

    is_resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    resolution_summary: Optional[str] = None

    extraction_confidence: float = 0.0

    related_event_ids: list[str] = field(default_factory=list)
    pattern_id: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# SC-3 Social Pattern
# ════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════
# SC-4 Coaching Opportunity
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class CoachingOpportunity:
    opportunity_detected: bool = False
    coaching_type: Optional[str] = None

    triggering_pattern: Optional[SocialPattern] = None
    triggering_event: Optional[SocialEvent] = None
    triggering_person: Optional[str] = None     # person_id

    delivery_mode: str = DeliveryMode.DEFERRED.value
    urgency: str = Urgency.LOW.value

    observation_text: str = ""
    observation_framing: str = ""

    max_length_chars: int = 220
    requires_explicit_consent: bool = False


# ════════════════════════════════════════════════════════════════════════════
# §9 UWM Social-Context Update
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class SocialContextUpdate:
    nodes_added: list[str] = field(default_factory=list)
    nodes_updated: list[str] = field(default_factory=list)
    nodes_gone_stale: list[str] = field(default_factory=list)

    active_conflicts: list[dict] = field(default_factory=list)
    recent_positive_events: list[dict] = field(default_factory=list)

    patterns_newly_detected: list[str] = field(default_factory=list)
    patterns_resolved: list[str] = field(default_factory=list)

    support_network_size: int = 0
    support_network_health: str = SupportNetworkHealth.ISOLATED.value
    social_engagement_trend: str = SocialEngagementTrend.INSUFFICIENT_DATA.value


# ════════════════════════════════════════════════════════════════════════════
# SocialIntelligencePacket — Layer 5 output (architecture doc §8)
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class SocialIntelligencePacket:
    social_graph_updated: bool = False
    social_graph_version: int = 0

    events_detected: list[SocialEvent] = field(default_factory=list)
    events_pending_confirmation: list[SocialEvent] = field(default_factory=list)

    active_patterns: list[SocialPattern] = field(default_factory=list)

    coaching_opportunity_detected: bool = False
    coaching_opportunity: Optional[CoachingOpportunity] = None
    coaching_injected: bool = False
    coaching_deferred: bool = False

    # If None, the Layer 4 FinalResponsePacket passes through unchanged (§8).
    modified_response: Optional[FinalResponsePacket] = None

    proactive_coaching_queue: list[CoachingOpportunity] = field(default_factory=list)

    social_context_update: Optional[SocialContextUpdate] = None

    # Audit
    sc1_updated: bool = False
    sc2_events_found: int = 0
    sc3_patterns_evaluated: int = 0
    sc3_patterns_active: int = 0
    processing_latency_ms: int = 0
