"""SC-4 — Coaching Opportunity Detector (architecture doc §6).

Answers a single question: *given everything Layer 5 knows, is this the right moment to
offer a social observation or gentle coaching?* "Coaching" is non-directive — a thoughtful
observation, a gently named pattern, a perspective question — never diagnosis or advice.

Getting timing wrong is worse than not coaching at all, so the detector is deliberately
conservative: a three-gate model (availability → timing → recency) where the observation
must pass *all three* to be surfaced now. Anything that passes availability but fails
timing/recency is a valid observation that is *deferred* (queued for Layer 6), not
discarded. Default is silence, not intervention (§13 principle 4).

Deterministic; only PATTERN_REFLECTION / CONFLICT_NAVIGATION text may use an LLM, and
that generation lives in the orchestrator. Opportunity construction (from a pattern,
conflict, or support gap) lives in ``coaching_opportunities.py``; this module is the
three gates + the top-level orchestrator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer3_reasoning.schemas import BackgroundEmotionalState, EmotionClassification
from backend.layer5_relationship.coaching_opportunities import (
    build_opportunity_from_conflict,
    build_opportunity_from_pattern,
    build_support_network_nudge,
)
from backend.layer5_relationship.schemas import (
    CoachingOpportunity,
    CoachingType,
    DeliveryMode,
    SocialEvent,
    SocialEventType,
    SocialGraph,
    SocialPattern,
    Urgency,
)

# Receptive emotional states for inline coaching (architecture doc §6.4 Gate 2).
_RECEPTIVE_LABELS = {
    "neutral", "curiosity", "contentment", "frustration", "ambivalence", "relief",
}
_NEGATIVE_DRIFT_LABELS = {"significant_negative_drift", "deteriorating"}
_AFFIRMING_TYPES = {
    CoachingType.STRENGTH_ACKNOWLEDGMENT.value,
    CoachingType.SUPPORT_NETWORK_NUDGE.value,
}
_TOPIC_ADJACENT_MODES = {"social_coaching", "casual", "life_review"}
_OFF_TOPIC_OK_TYPES = {
    CoachingType.GENTLE_REFRAME.value,
    CoachingType.BOUNDARY_SUPPORT.value,
}

_HIGH_DISTRESS_VALENCE = -0.65
_SUPPORT_EROSION_DAYS = 45
_RECENCY_BLOCK_DAYS = 14
_MAX_SURFACE_WITHOUT_ACK = 3


def gate_1_availability(
    active_patterns: list[SocialPattern],
    recent_events: list[SocialEvent],
    social_graph: SocialGraph,
    now: Optional[datetime] = None,
) -> Optional[CoachingOpportunity]:
    """Is there something worth saying? Returns the highest-priority observation (§6.4)."""
    now = now or datetime.utcnow()

    # Priority 1: active patterns, unsurfaced (conf >= 0.70) or acknowledged & gone quiet 30d+.
    unsurfaced = [p for p in active_patterns
                  if not p.has_been_surfaced and p.pattern_confidence >= 0.70]
    acknowledged = [p for p in active_patterns
                    if p.user_acknowledged and p.last_activation
                    and (now - p.last_activation).days > 30]
    candidates = sorted(unsurfaced + acknowledged, key=lambda p: p.pattern_strength, reverse=True)
    if candidates:
        best = candidates[0]
        person_id = best.person_ids_involved[0] if best.person_ids_involved else None
        node = social_graph.nodes.get(person_id) if person_id else None
        return build_opportunity_from_pattern(best, node.display_name if node else "")

    # Priority 2: high-intensity unresolved conflict.
    active_conflicts = [
        e for e in recent_events
        if e.event_type in (SocialEventType.CONFLICT_ONSET.value,
                            SocialEventType.CONFLICT_ESCALATION.value)
        and not e.is_resolved and e.emotional_intensity > 0.6
    ]
    if active_conflicts:
        return build_opportunity_from_conflict(active_conflicts[0], social_graph)

    # Priority 3: support-network erosion.
    support_sources = [n for n in social_graph.nodes.values() if n.is_support_source]
    dated_sources = [n for n in support_sources if n.last_mentioned]
    if dated_sources:
        days_since = min((now - n.last_mentioned).days for n in dated_sources)
        if days_since > _SUPPORT_EROSION_DAYS:
            return build_support_network_nudge(support_sources)

    return None


def gate_2_timing(
    opportunity: CoachingOpportunity,
    conversation_mode: str,
    primary_emotion: EmotionClassification,
    background_state: BackgroundEmotionalState,
    relationship_stage: str,
    circadian_band: str,
) -> bool:
    """Is now the right moment? Conservative — defaults to False in ambiguity (§6.4)."""
    # Hard blocks.
    if conversation_mode == "crisis":
        return False
    if primary_emotion.crisis_flag:
        return False
    if primary_emotion.valence < _HIGH_DISTRESS_VALENCE:
        return False
    if circadian_band == "late_night" and opportunity.urgency != Urgency.HIGH.value:
        return False
    if relationship_stage in ("new", "acquaintance"):
        return False

    # Soft block: when the user is struggling, only affirming coaching.
    if background_state.bes_label in _NEGATIVE_DRIFT_LABELS:
        if opportunity.coaching_type not in _AFFIRMING_TYPES:
            return False

    # Emotional receptivity for inline delivery.
    if primary_emotion.primary_label not in _RECEPTIVE_LABELS:
        if opportunity.delivery_mode == DeliveryMode.INLINE.value:
            return False

    # Topic adjacency for the current conversation mode.
    if conversation_mode not in _TOPIC_ADJACENT_MODES:
        if opportunity.coaching_type not in _OFF_TOPIC_OK_TYPES:
            opportunity.delivery_mode = DeliveryMode.DEFERRED.value
            return False

    return True


def gate_3_recency(
    opportunity: CoachingOpportunity,
    pattern: Optional[SocialPattern],
    now: Optional[datetime] = None,
) -> bool:
    """Has this been said too recently / too often? (architecture doc §6.4)."""
    if pattern is None:
        return True
    now = now or datetime.utcnow()
    if pattern.has_been_surfaced:
        if pattern.last_observed and (now - pattern.last_observed).days < _RECENCY_BLOCK_DAYS:
            return False
        if pattern.surface_count >= _MAX_SURFACE_WITHOUT_ACK and not pattern.user_acknowledged:
            return False
    return True


def detect_coaching_opportunity(
    active_patterns: list[SocialPattern],
    recent_events: list[SocialEvent],
    social_graph: SocialGraph,
    conversation_mode: str,
    primary_emotion: EmotionClassification,
    background_state: BackgroundEmotionalState,
    relationship_stage: str,
    circadian_band: str,
    now: Optional[datetime] = None,
) -> CoachingOpportunity:
    """Run all three gates (architecture doc §6.4).

    Returns an opportunity with ``opportunity_detected=True`` only when every gate passes.
    A candidate that passes availability but fails timing/recency is returned with
    ``opportunity_detected=False`` and ``delivery_mode='deferred'`` so the orchestrator can
    queue it for Layer 6. When nothing is available, returns an empty opportunity.
    """
    now = now or datetime.utcnow()
    opp = gate_1_availability(active_patterns, recent_events, social_graph, now=now)
    if opp is None:
        return CoachingOpportunity(opportunity_detected=False)

    pattern = opp.triggering_pattern
    if not gate_2_timing(opp, conversation_mode, primary_emotion, background_state,
                         relationship_stage, circadian_band):
        opp.opportunity_detected = False
        opp.delivery_mode = DeliveryMode.DEFERRED.value
        return opp
    if not gate_3_recency(opp, pattern, now=now):
        opp.opportunity_detected = False
        opp.delivery_mode = DeliveryMode.DEFERRED.value
        return opp

    opp.opportunity_detected = True
    return opp
