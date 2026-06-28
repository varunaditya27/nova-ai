"""Layer 5 — Social Intelligence & Coaching.

Core question: *what does Nova understand about the people in the user's life and the
social dynamics between them?* Layer 5 accumulates social knowledge across sessions and
uses it to offer coaching, perspective, and pattern recognition the user cannot always
give themselves (architecture doc §1). It is not a therapy or crisis layer.

Five sub-components produce the read-only ``SocialIntelligencePacket`` (consumed by
Layers 6, 7, 9, and written back to the Layer 2 UWM social context):

    SC-1  social_graph.py        — Social Graph Manager (entity resolution, node lifecycle)
    SC-2  event_tracker.py       — Interpersonal Event Tracker (rule + LLM event extraction)
    SC-3  pattern_recognizer.py  — Social Pattern Recognizer (intra/cross/temporal, batch)
    SC-4  coaching_detector.py   — Coaching Opportunity Detector (conservative 3-gate model)
    SC-5  coaching_modifier.py   — Social Coaching Response Modifier (natural injection)

    packet_builder.build_social_intelligence_packet orchestrates the coaching path.

Design invariants honored here (architecture doc §10, §13):
- Social context is longitudinal, not per-message (SC-1..SC-3 operate over sessions).
- The graph is what the user *said*, never what Nova inferred (``data_source="user_stated"``).
- Third parties are not in the room — observations are framed as accounts, not facts.
- Coaching is offered, not imposed — the 3-gate model defaults to silence.
- Pattern reflection is always provisional (noticed, not concluded).
- Layer 5 never blocks delivery of the Layer 4 response (§11 hard rule).

Reconciliation: the May-28 scaffold modelled this layer as the Nova↔user relationship
(``relationship_manager`` / ``tie_strength_calculator`` / ``self_disclosure_engine``) — but
that is Layer 4's domain (RelationshipState, tie strength, self-disclosure gating, all built
in Layer 4 SC-2/SC-3). Those modules were removed; Layer 5 is the *user's social world*
(third parties). The scaffold's ``social_coaching`` is split into ``coaching_detector`` (SC-4)
and ``coaching_modifier`` (SC-5). See architecture doc §14 for the full as-built mapping.
The two LLM uses (event extraction, pattern-reflection text) are injected as callables so
the layer runs and tests offline.
"""

from backend.layer5_relationship.packet_builder import (
    build_social_context_update,
    build_social_intelligence_packet,
)
from backend.layer5_relationship.social_graph import (
    create_node,
    decay_confidence,
    infer_relationship_from_context,
    is_tentative_match,
    resolve_entity,
    update_node_valence,
)
from backend.layer5_relationship.event_tracker import (
    detect_events_rule_based,
    extract_events,
)
from backend.layer5_relationship.pattern_recognizer import (
    cluster_by_semantic_similarity,
    compute_mention_counts_by_window,
    detect_patterns,
    is_declining_trend,
)
from backend.layer5_relationship.coaching_detector import (
    detect_coaching_opportunity,
    gate_1_availability,
    gate_2_timing,
    gate_3_recency,
)
from backend.layer5_relationship.coaching_modifier import (
    inject_observation,
    select_transition,
)
from backend.layer5_relationship.schemas import (
    CoachingOpportunity,
    CoachingType,
    SocialContextUpdate,
    SocialEvent,
    SocialEventType,
    SocialGraph,
    SocialIntelligencePacket,
    SocialNode,
    SocialPattern,
    SocialPatternType,
)

__all__ = [
    "build_social_intelligence_packet",
    "build_social_context_update",
    "resolve_entity",
    "infer_relationship_from_context",
    "is_tentative_match",
    "create_node",
    "update_node_valence",
    "decay_confidence",
    "detect_events_rule_based",
    "extract_events",
    "detect_patterns",
    "cluster_by_semantic_similarity",
    "compute_mention_counts_by_window",
    "is_declining_trend",
    "detect_coaching_opportunity",
    "gate_1_availability",
    "gate_2_timing",
    "gate_3_recency",
    "inject_observation",
    "select_transition",
    "CoachingOpportunity",
    "CoachingType",
    "SocialContextUpdate",
    "SocialEvent",
    "SocialEventType",
    "SocialGraph",
    "SocialIntelligencePacket",
    "SocialNode",
    "SocialPattern",
    "SocialPatternType",
]
