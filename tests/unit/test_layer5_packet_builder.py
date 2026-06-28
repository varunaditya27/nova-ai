"""Tests for the Layer 5 orchestrator / SocialIntelligencePacket builder (architecture doc §8, §11)."""

from datetime import datetime

from backend.layer5_relationship import packet_builder as pb
from backend.layer5_relationship.schemas import (
    SocialEvent,
    SocialEventType,
    SocialGraph,
    SocialIntelligencePacket,
    SocialNode,
    SocialPattern,
    SocialPatternType,
    SupportNetworkHealth,
    VoiceParameters,
)
from backend.layer4_persona.schemas import FinalResponsePacket
from backend.layer2_memory.schemas import ConversationMode
from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    EmotionClassification,
    EmotionIntentPacket,
    EmotionLabel,
)

NOW = datetime(2026, 6, 28)


def _emotion_packet(mode=ConversationMode.SOCIAL_COACHING.value, label=EmotionLabel.NEUTRAL.value,
                    valence=0.0, crisis=False):
    return EmotionIntentPacket(
        primary_emotion=EmotionClassification(primary_label=label, valence=valence,
                                              crisis_flag=crisis),
        background_state=BackgroundEmotionalState(),
        conversation_mode=mode, crisis_active=crisis)


def _response(text="That sounds like a lot. It makes sense that you're worn out."):
    return FinalResponsePacket(final_text=text, conversation_mode=ConversationMode.SOCIAL_COACHING.value,
                               topic_domain="relationships")


def _pattern():
    return SocialPattern(pattern_type=SocialPatternType.RECURRING_CONFLICT_TOPIC.value,
                         person_ids_involved=["p1"], pattern_confidence=0.85, pattern_strength=0.6,
                         plain_language_description="You've described conflict with Riya a few times.",
                         coaching_hook="a recurring conflict theme with Riya",
                         has_been_surfaced=False, last_activation=NOW, last_observed=NOW)


def _graph():
    return SocialGraph(nodes={"p1": SocialNode(person_id="p1", display_name="Riya")}, version=3)


# ── No opportunity → pass through (§8) ───────────────────────────────────────
def test_no_opportunity_passes_response_through():
    pkt = pb.build_social_intelligence_packet(
        _response(), _emotion_packet(), social_graph=_graph(), active_patterns=[], now=NOW)
    assert isinstance(pkt, SocialIntelligencePacket)
    assert pkt.coaching_opportunity_detected is False
    assert pkt.modified_response is None


# ── Opportunity injected (§7, §8) ────────────────────────────────────────────
def test_opportunity_injected_modifies_response():
    pkt = pb.build_social_intelligence_packet(
        _response(), _emotion_packet(), social_graph=_graph(), active_patterns=[_pattern()],
        relationship_stage="established", voice_parameters=VoiceParameters(max_response_length_chars=800),
        now=NOW)
    assert pkt.coaching_opportunity_detected is True
    assert pkt.coaching_injected is True
    assert pkt.modified_response is not None
    assert pkt.modified_response.social_coaching_injected is True
    assert "riya" in pkt.modified_response.final_text.lower()


# ── Timing fails → deferred to Layer 6 (§8, §11) ─────────────────────────────
def test_deferred_when_timing_fails_queues_for_layer6():
    pkt = pb.build_social_intelligence_packet(
        _response(), _emotion_packet(mode=ConversationMode.CRISIS.value, crisis=True),
        social_graph=_graph(), active_patterns=[_pattern()], now=NOW)
    assert pkt.coaching_opportunity_detected is False
    assert pkt.coaching_deferred is True
    assert len(pkt.proactive_coaching_queue) == 1
    assert pkt.modified_response is None


# ── LLM regenerates pattern-reflection text (§6.5) ───────────────────────────
def test_llm_regenerates_pattern_reflection_text():
    def fake_llm(prompt):
        return "I've noticed you and Riya keep circling the same disagreement — does that ring true?"

    pkt = pb.build_social_intelligence_packet(
        _response(), _emotion_packet(), social_graph=_graph(), active_patterns=[_pattern()],
        relationship_stage="established", observation_llm_fn=fake_llm, now=NOW)
    assert pkt.coaching_injected is True
    assert "circling the same disagreement" in pkt.modified_response.final_text.lower()


# ── §11 hard rule: never block the Layer 4 response ──────────────────────────
def test_never_blocks_on_internal_error():
    # Passing None for the emotion packet would raise inside detection; the orchestrator
    # must swallow it and pass the Layer 4 response through unchanged.
    pkt = pb.build_social_intelligence_packet(
        _response(), None, social_graph=_graph(), active_patterns=[_pattern()], now=NOW)
    assert isinstance(pkt, SocialIntelligencePacket)
    assert pkt.modified_response is None
    assert pkt.coaching_injected is False


# ── Audit counts (§8) ────────────────────────────────────────────────────────
def test_audit_counts_populated():
    events = [SocialEvent(person_id="p1", event_type=SocialEventType.CONFLICT_ONSET.value,
                          reported_timestamp=NOW)]
    pkt = pb.build_social_intelligence_packet(
        _response(), _emotion_packet(), social_graph=_graph(), active_patterns=[_pattern()],
        events_detected=events, relationship_stage="established", now=NOW)
    assert pkt.sc2_events_found == 1
    assert pkt.sc3_patterns_active == 1
    assert pkt.social_graph_version == 3


# ── UWM social-context update (§9) ───────────────────────────────────────────
def test_social_context_update_health():
    isolated = pb.build_social_context_update(SocialGraph(nodes={}), [], now=NOW)
    assert isolated.support_network_health == SupportNetworkHealth.ISOLATED.value
    assert isolated.support_network_size == 0

    robust_graph = SocialGraph(nodes={
        f"p{i}": SocialNode(person_id=f"p{i}", is_support_source=True) for i in range(3)})
    robust = pb.build_social_context_update(robust_graph, [], now=NOW)
    assert robust.support_network_health == SupportNetworkHealth.ROBUST.value
    assert robust.support_network_size == 3
