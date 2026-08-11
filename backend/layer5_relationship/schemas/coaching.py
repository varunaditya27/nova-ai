"""SC-4 Coaching Opportunity, §9 UWM social-context update, and the Layer 5 output
SocialIntelligencePacket (architecture doc §6, §8, §9).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.layer4_persona.schemas import FinalResponsePacket

from .enums import DeliveryMode, SocialEngagementTrend, SupportNetworkHealth, Urgency
from .events import SocialEvent
from .patterns import SocialPattern


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
