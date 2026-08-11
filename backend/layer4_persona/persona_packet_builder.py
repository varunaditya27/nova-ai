"""Layer 4 §6.4 — compose the read-only PersonaPacket from SC-1..SC-4 outputs.

Split out of ``packet_builder.py``: this is packet assembly/translation, not the
SC-5/SC-6 generation orchestration.
"""

from __future__ import annotations

from datetime import datetime

from backend.layer3_reasoning.schemas import EmotionIntentPacket
from backend.layer4_persona.schemas import (
    DriftDetectionResult,
    FinalResponsePacket,
    MemoryReferencePolicy,
    PersonaPacket,
    PersonaState,
    RelationshipState,
    SemanticDraft,
    VoiceParameters,
)

# Graceful refusal used when a critical drift (role abandonment) is detected (§11 Rule 4).
# Also imported directly by api/assembly.py's live plan()/refine() critical-drift short-circuit.
GRACEFUL_REFUSAL_TEXT = (
    "I want to stay honest with you about what I am — I'm Nova, and I'm here as myself "
    "rather than pretending to be someone I'm not. I'd love to keep talking, though. "
    "What's underneath the ask — is there something you're hoping to get from this?"
)

# Plain-language memory-reference policy strings for the PersonaPacket (§6.4).
_MEMORY_POLICY_TEXT = {
    MemoryReferencePolicy.NONE.value:
        "Do not reference past conversations or invent shared history.",
    MemoryReferencePolicy.SOFT.value:
        "You may make soft, vague references to the past (e.g. 'something you mentioned before').",
    MemoryReferencePolicy.EPISODIC.value:
        "You may reference specific past episodes when relevant.",
    MemoryReferencePolicy.FULL.value:
        "You may reference specific episodes and longer-term patterns explicitly.",
}


def _warmth_phrase(level: float) -> str:
    if level >= 0.8:
        return "high — respond with personal warmth and unhurried care"
    if level >= 0.55:
        return "moderate — friendly and personable"
    if level >= 0.3:
        return "measured — present but not effusive"
    return "low — plain and professional"


def assemble_persona_packet(
    persona_state: PersonaState,
    relationship_state: RelationshipState,
    voice_parameters: VoiceParameters,
    drift_result: DriftDetectionResult,
) -> PersonaPacket:
    """Compose the read-only PersonaPacket consumed by SC-5/SC-6 (architecture doc §6.4)."""
    constraints = [
        "Do not claim to have human feelings or experiences you do not have.",
        "Do not be sycophantic; do not validate everything.",
        "Hold your positions when warranted; you may disagree.",
        "Do not catastrophize or amplify negative emotions.",
    ]
    if drift_result.planner_directive:
        constraints.append(drift_result.planner_directive)

    if voice_parameters.follow_up_question_allowed and voice_parameters.follow_up_question_max > 0:
        question_policy = (
            f"You may ask up to {voice_parameters.follow_up_question_max} "
            f"{voice_parameters.question_type} follow-up question(s)."
        )
    else:
        question_policy = "Do not ask follow-up questions this turn."

    return PersonaPacket(
        persona_state=persona_state,
        relationship_state=relationship_state,
        voice_parameters=voice_parameters,
        drift_check_result=drift_result,
        persona_instruction=(
            f"You are {persona_state.name}. {persona_state.character_description} "
            f"{persona_state.primary_orientation}"
        ),
        tone_instruction=(
            f"Register: {voice_parameters.register}. "
            f"Warmth: {_warmth_phrase(voice_parameters.warmth_expression)}. "
            f"Humor: {voice_parameters.humor_mode}."
        ),
        constraint_instruction=" ".join(constraints),
        memory_reference_policy=_MEMORY_POLICY_TEXT.get(
            relationship_state.memory_reference_policy, ""
        ),
        question_policy=question_policy,
        length_instruction=(
            f"Target length: {voice_parameters.target_response_length}; "
            f"hard ceiling {voice_parameters.max_response_length_chars} characters."
        ),
        assembled_at=datetime.utcnow(),
    )


def drift_override_packet(
    emotion_packet: EmotionIntentPacket,
    drift_result: DriftDetectionResult,
    emotional_intensity: float,
    now: datetime,
) -> FinalResponsePacket:
    """Critical-drift refusal: never run the planners, always this graceful decline (§12)."""
    fallback = GRACEFUL_REFUSAL_TEXT
    return FinalResponsePacket(
        final_text=fallback,
        semantic_draft=SemanticDraft(text=fallback, word_count=len(fallback.split())),
        refinement_applied=False,
        refinement_skipped_reason="drift_override",
        drift_check_result=drift_result,
        complexity_score=0.0,
        emotional_intensity=emotional_intensity,
        conversation_mode=emotion_packet.conversation_mode,
        suggested_thinking_pause_ms=emotion_packet.suggested_thinking_pause_ms,
        topic_domain=emotion_packet.topic_domain,
        intent_served=emotion_packet.intent.primary_intent,
        response_generated_at=now,
    )
