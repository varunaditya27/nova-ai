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

Split by sub-component into submodules; this ``__init__`` re-exports everything so
``from backend.layer5_relationship.schemas import X`` keeps working unchanged.
"""

from __future__ import annotations

# Upstream types (single source of truth).
from backend.layer4_persona.schemas import (  # noqa: F401  (re-exported)
    FinalResponsePacket,
    VoiceParameters,
)

from .coaching import CoachingOpportunity, SocialContextUpdate, SocialIntelligencePacket
from .enums import (
    CoachingType,
    DeliveryMode,
    InteractionFrequency,
    PatternScope,
    Recency,
    RelationshipType,
    SocialEngagementTrend,
    SocialEventType,
    SocialPatternType,
    SupportNetworkHealth,
    Urgency,
)
from .events import SocialEvent
from .graph import SocialEdge, SocialGraph, SocialNode
from .patterns import SocialPattern

__all__ = [
    "CoachingOpportunity",
    "CoachingType",
    "DeliveryMode",
    "FinalResponsePacket",
    "InteractionFrequency",
    "PatternScope",
    "Recency",
    "RelationshipType",
    "SocialContextUpdate",
    "SocialEdge",
    "SocialEngagementTrend",
    "SocialEvent",
    "SocialEventType",
    "SocialGraph",
    "SocialIntelligencePacket",
    "SocialNode",
    "SocialPattern",
    "SocialPatternType",
    "SupportNetworkHealth",
    "Urgency",
    "VoiceParameters",
]
