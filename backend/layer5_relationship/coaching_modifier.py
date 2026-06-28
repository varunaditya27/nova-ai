"""SC-5 — Social Coaching Response Modifier (architecture doc §7).

Takes the ``CoachingOpportunity`` from SC-4 and the Layer 4 ``FinalResponsePacket`` and
produces a response that integrates the observation *naturally*. It augments the Layer 4
response; it never replaces it. A coaching observation bolted on awkwardly breaks flow and
feels intrusive — so the modifier picks the right structural position, transition, and
phrasing weight (§7.1).

Three injection modes (§7.2): inline (soft transition + observation), as_question (the
observation as the final element), and deferred/proactive_future (no change this turn —
the observation is handed to Layer 6). A headroom guard defers rather than overflow the
voice length ceiling (§7.3, §11).

Deterministic; no LLM call (the observation text was produced upstream).
"""

from __future__ import annotations

from dataclasses import replace

from backend.layer4_persona.schemas import FinalResponsePacket
from backend.layer5_relationship.schemas import (
    CoachingOpportunity,
    DeliveryMode,
    VoiceParameters,
)

# Soft transition phrases by relationship stage (architecture doc §7.2).
_TRANSITIONS = {
    "close": "I've also been thinking —",
    "established": "One thing that's been on my mind —",
    "developing": "Can I add something I've noticed?",
    "acquaintance": "Unrelated, but —",
    "new": "Unrelated, but —",
}

# Voice register → pseudo relationship stage for transition selection.
_REGISTER_STAGE = {
    "intimate": "close",
    "casual": "established",
    "natural": "developing",
    "professional": "acquaintance",
    "formal": "acquaintance",
}

_PASS_THROUGH_MODES = {DeliveryMode.DEFERRED.value, DeliveryMode.PROACTIVE_FUTURE.value}


def select_transition(relationship_stage: str, coaching_type: str) -> str:
    """Pick a soft transition phrase for inline injection (architecture doc §7.2)."""
    return _TRANSITIONS.get(relationship_stage, _TRANSITIONS["developing"])


def inject_observation(
    final_response: FinalResponsePacket,
    opportunity: CoachingOpportunity,
    voice_parameters: VoiceParameters,
) -> FinalResponsePacket:
    """Integrate the coaching observation into the Layer 4 response (architecture doc §7.3).

    Returns the response unchanged for deferred/proactive modes or when there isn't enough
    length headroom (in which case the opportunity is flipped to ``deferred`` for Layer 6).
    Otherwise returns a new packet with the observation appended and coaching metadata set.
    """
    if opportunity.delivery_mode in _PASS_THROUGH_MODES:
        return final_response

    headroom = voice_parameters.max_response_length_chars - len(final_response.final_text)
    if headroom < opportunity.max_length_chars:
        opportunity.delivery_mode = DeliveryMode.DEFERRED.value
        return final_response

    body = final_response.final_text.rstrip()
    if opportunity.delivery_mode == DeliveryMode.AS_QUESTION.value:
        modified_text = f"{body}\n\n{opportunity.observation_text}"
    else:
        stage = _REGISTER_STAGE.get(voice_parameters.register, "developing")
        transition = select_transition(stage, opportunity.coaching_type)
        modified_text = f"{body}\n\n{transition} {opportunity.observation_text}"

    return replace(
        final_response,
        final_text=modified_text,
        social_coaching_injected=True,
        coaching_type_injected=opportunity.coaching_type,
        coaching_person_id=opportunity.triggering_person,
    )
