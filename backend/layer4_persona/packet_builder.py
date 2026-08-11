"""Layer 4 orchestrator — assembles the PersonaPacket and emits the FinalResponsePacket.

Runs the six sub-components in order (architecture doc §2):

    SC-1 resolve_persona_state        →  PersonaState
    SC-2 compute_relationship_state   →  RelationshipState
    SC-3 calibrate_voice              →  VoiceParameters
    SC-4 detect_drift                 →  DriftDetectionResult
        └─ assemble PersonaPacket (plain-language instruction strings)
    SC-5 generate_semantic_draft      →  SemanticDraft   (LLM via planner_llm_fn)
    SC-6 refine_emotion               →  RefinementOutput (LLM via refiner_llm_fn)
        └─ FinalResponsePacket

Hard rules (architecture doc §12):
- Layer 4 ALWAYS emits a ``FinalResponsePacket`` with non-empty ``final_text``.
- A critical drift (role abandonment) overrides both planners with a graceful refusal —
  the planner's capitulating content never reaches the user.
- Each sub-component is wrapped so a single failure degrades quality, never the packet.

The two LLM calls are injected (``planner_llm_fn`` / ``refiner_llm_fn``) so the whole
layer runs and tests offline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer3_reasoning.schemas import EmotionIntentPacket
from backend.layer4_persona import (
    drift_detector,
    emotion_refiner,
    persona_resolver,
    relationship_manager,
    semantic_planner,
    tone_calibrator,
)
from backend.layer4_persona.persona_packet_builder import (
    GRACEFUL_REFUSAL_TEXT,
    assemble_persona_packet,
    drift_override_packet,
)
from backend.layer4_persona.schemas import (
    DriftDetectionResult,
    FinalResponsePacket,
    PersonaState,
    RecommendedAction,
    RelationshipState,
    SemanticDraft,
    VoiceParameters,
)

__all__ = ["GRACEFUL_REFUSAL_TEXT", "build_final_response_packet"]


def _safe(fn: Callable, fallback):
    """Run ``fn``; on any exception return ``fallback`` (§12 degrade-don't-fail)."""
    try:
        return fn()
    except Exception:
        return fallback


def build_final_response_packet(
    emotion_packet: EmotionIntentPacket,
    user_message: str,
    circadian_band: str = "afternoon",
    persisted_relationship: Optional[RelationshipState] = None,
    communication_model=None,
    psychological_model=None,
    dynamic_properties=None,
    recalled_memories=None,
    nova_recent_positions=None,
    explicitly_asked_for_advice: bool = False,
    planner_llm_fn: Optional[Callable[[str], str]] = None,
    refiner_llm_fn: Optional[Callable[[str], str]] = None,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
    now: Optional[datetime] = None,
) -> FinalResponsePacket:
    """Run Layer 4 end-to-end and return the FinalResponsePacket (architecture doc §9, §12)."""
    now = now or datetime.utcnow()
    mode = emotion_packet.conversation_mode
    emotional_intensity = _safe(
        lambda: emotion_packet.primary_emotion.intensity, 0.0
    )

    # ── SC-1..SC-4 (deterministic Persona Engine) ────────────────────────────
    persona_state = _safe(
        lambda: persona_resolver.resolve_persona_state(
            psychological_model=psychological_model,
            communication_model=communication_model,
            dynamic_properties=dynamic_properties,
            session_context={"conversation_mode": mode},
        ),
        PersonaState(),
    )
    relationship_state = _safe(
        lambda: relationship_manager.compute_relationship_state(
            persisted=persisted_relationship, communication_model=communication_model
        ),
        RelationshipState(),
    )
    voice_parameters = _safe(
        lambda: tone_calibrator.calibrate_voice(
            conversation_mode=mode, circadian_band=circadian_band,
            relationship_state=relationship_state, persona_state=persona_state,
            background_state=emotion_packet.background_state,
        ),
        VoiceParameters(),
    )
    drift_result = _safe(
        lambda: drift_detector.detect_drift(
            user_message=user_message, persona_state=persona_state,
            nova_recent_positions=nova_recent_positions,
        ),
        DriftDetectionResult(),
    )

    persona_packet = assemble_persona_packet(
        persona_state, relationship_state, voice_parameters, drift_result
    )

    # ── Critical drift override: refuse gracefully, never run the planners (§12) ──
    if drift_result.recommended_action == RecommendedAction.REFUSE_GRACEFULLY.value:
        return drift_override_packet(emotion_packet, drift_result, emotional_intensity, now)

    # Inject a hold-position / redirect directive into the response instruction.
    response_instruction = emotion_packet.response_instruction
    if drift_result.planner_directive and drift_result.recommended_action in (
        RecommendedAction.HOLD_POSITION.value, RecommendedAction.REDIRECT.value,
        RecommendedAction.ADD_CAVEAT.value,
    ):
        response_instruction = f"{response_instruction}\n{drift_result.planner_directive}"

    # ── SC-5 Semantic Planner ────────────────────────────────────────────────
    draft = _safe(
        lambda: semantic_planner.generate_semantic_draft(
            user_message,
            persona_packet=persona_packet,
            advice_gate=emotion_packet.advice_gate,
            prefers_no_advice=emotion_packet.prefers_no_advice,
            explicitly_asked_for_advice=explicitly_asked_for_advice,
            response_instruction=response_instruction,
            recalled_memories=recalled_memories,
            max_response_length_chars=voice_parameters.max_response_length_chars,
            circadian_band=circadian_band,
            llm_fn=planner_llm_fn,
        ),
        SemanticDraft(text=semantic_planner._FALLBACK_DRAFT_TEXT),
    )

    # ── SC-6 Emotion Refiner (skip per the five neutral conditions) ──────────
    skip = _safe(
        lambda: emotion_refiner.should_skip_refinement(
            primary_label=emotion_packet.primary_emotion.primary_label,
            bes_label=emotion_packet.background_state.bes_label,
            mismatch_detected=emotion_packet.mismatch.mismatch_detected,
            primary_intent=emotion_packet.intent.primary_intent,
            crisis_active=emotion_packet.crisis_active,
        ),
        False,
    )
    refinement = _safe(
        lambda: emotion_refiner.refine_emotion(
            draft, skip=skip,
            voice_parameters=voice_parameters,
            emotional_posture_instruction=emotion_packet.emotional_posture_instruction,
            persona_packet=persona_packet,
            primary_emotion_label=emotion_packet.primary_emotion.primary_label,
            bes_label_description=emotion_packet.background_state.bes_label,
            primary_feeling=emotion_packet.empathy_hypothesis.primary_feeling,
            primary_need=emotion_packet.empathy_hypothesis.primary_need,
            llm_fn=refiner_llm_fn,
            similarity_fn=similarity_fn,
        ),
        emotion_refiner.RefinementOutput(final_text=draft.text, refinement_applied=False),
    )

    final_text = refinement.final_text or draft.text or semantic_planner._FALLBACK_DRAFT_TEXT

    return FinalResponsePacket(
        final_text=final_text,
        semantic_draft=draft,
        refinement_applied=refinement.refinement_applied,
        refinement_skipped_reason=refinement.refinement_skipped_reason,
        advice_gate_passed=not draft.advice_included
        if emotion_packet.advice_gate == "closed" else True,
        factual_validation_passed=refinement.factual_validation_passed,
        factual_claims_reinserted=refinement.factual_claims_reinserted,
        drift_check_result=drift_result,
        complexity_score=draft.complexity_score,
        emotional_intensity=emotional_intensity,
        conversation_mode=mode,
        suggested_thinking_pause_ms=emotion_packet.suggested_thinking_pause_ms,
        memory_references_used=draft.memory_references_used,
        thread_addressed=draft.thread_addressed,
        topic_domain=emotion_packet.topic_domain,
        intent_served=emotion_packet.intent.primary_intent,
        response_generated_at=now,
    )
