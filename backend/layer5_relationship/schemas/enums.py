"""Enumerations for Layer 5 — Social Intelligence & Coaching."""

from __future__ import annotations

from enum import Enum


# ── SC-1 Social Graph enums ─────────────────────────────────────────────────
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


# ── SC-2 Event enums ─────────────────────────────────────────────────────────
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


# ── SC-3 Pattern enums ───────────────────────────────────────────────────────
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


# ── SC-4 Coaching enums ──────────────────────────────────────────────────────
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


# ── §9 UWM social-context enums ─────────────────────────────────────────────
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
