"""Layer 9 engine entry point (architecture doc §7, §8).

``deliver`` runs SC-4 → SC-2 → SC-1 (→ SC-3 for voice) and returns a Layer9Output. Crisis mode
is a single hard override threaded through every SC. Every sub-step is wrapped so a failure
degrades to plain delivery rather than blocking the response (§9).
"""

from __future__ import annotations

import random as _random
import time
from typing import Optional

from backend.layer9_output import (
    format_adapter,
    micro_interaction_engine,
    self_edit_simulator,
    thinking_pause as thinking_pause_mod,
    voice_synthesizer,
)
from backend.layer9_output.interaction_orchestrator import _safe, orchestrate_output
from backend.layer9_output.length_calibrator import compute_length_target
from backend.layer9_output.schemas import (
    FormatSpec,
    Layer9Output,
    MicroInteractionPlan,
    OrchestratedOutput,
    Structure,
    UserFormatProfile,
)


def deliver(
    final_response_text: str,
    conversation_mode: str,
    *,
    content_type: str = "general",
    relationship_stage: str = "friend",
    emotional_intensity: float = 0.0,
    complexity_score: float = 0.0,
    urgency_level: float = 0.0,
    circadian_band: str = "afternoon",
    turn_type: str = "casual",
    voice_mode: bool = False,
    crisis_mode_active: bool = False,
    semantic_draft: Optional[str] = None,
    user_format_profile: Optional[UserFormatProfile] = None,
    tts_backend=None,
    is_proactive: bool = False,
    farewell_detected: bool = False,
    correction_armed: bool = False,
    user_message_length: int = 0,
    consecutive_user_messages: int = 0,
    messages_since_last_ack: int = 99,
    num_entities: int = 0,
    rng=_random,
) -> Layer9Output:
    """Run the full Layer 9 pipeline → Layer9Output (architecture doc §7, §8)."""
    start = time.perf_counter()
    profile = user_format_profile or UserFormatProfile()

    # SC-4: format spec (+ length target) — safe default on failure (§9).
    format_spec = _safe(lambda: format_adapter.compute_format_spec(
        conversation_mode=conversation_mode, content_type=content_type,
        relationship_stage=relationship_stage, emotional_intensity=emotional_intensity,
        voice_mode=voice_mode, user_format_profile=profile,
        crisis_mode_active=crisis_mode_active, num_entities=num_entities), None)
    if format_spec is None:
        format_spec = FormatSpec(structure=Structure.PURE_PROSE.value)

    length_target = _safe(lambda: compute_length_target(
        conversation_mode, emotional_intensity, content_type, turn_type, relationship_stage,
        profile.preferred_length), (0, 0))
    format_spec.target_length_min_chars, format_spec.target_length_max_chars = length_target

    # Post-generation format enforcement (hard backstop).
    clean_text = _safe(lambda: format_adapter.enforce_format_spec(final_response_text, format_spec),
                       final_response_text)

    # SC-2: micro-interaction plan.
    micro_plan = _safe(lambda: micro_interaction_engine.plan_micro_interactions(
        conversation_mode=conversation_mode, relationship_stage=relationship_stage,
        emotional_intensity=emotional_intensity, turn_type=turn_type,
        user_message_length=user_message_length,
        consecutive_user_messages=consecutive_user_messages, complexity_score=complexity_score,
        messages_since_last_ack=messages_since_last_ack, correction_armed=correction_armed,
        is_proactive=is_proactive, farewell_detected=farewell_detected,
        crisis_mode_active=crisis_mode_active, rng=rng), MicroInteractionPlan())

    # SC-1: thinking pause + self-edit.
    pause_ms = _safe(lambda: thinking_pause_mod.compute_thinking_pause(
        complexity_score, emotional_intensity, urgency_level, circadian_band, conversation_mode,
        relationship_stage, crisis_mode_active, rng=rng), 0)
    self_edit_plan = None
    if semantic_draft and not crisis_mode_active:
        self_edit_plan = _safe(lambda: self_edit_simulator.plan_self_edit(
            semantic_draft, clean_text, complexity_score, relationship_stage,
            conversation_mode, rng=rng), None)

    # SC-3: voice (optional, parallel in production).
    ssml_document = None
    audio_result = None
    if voice_mode and not crisis_mode_active:
        doc = _safe(lambda: voice_synthesizer.generate_ssml(
            clean_text, conversation_mode, circadian_band, relationship_stage,
            include_fillers=True,
            apply_transforms=format_spec.voice_content_transform_required, rng=rng), None)
        if doc is not None:
            ssml_document = doc.ssml
        if tts_backend is not None:
            audio_result = _safe(lambda: voice_synthesizer.synthesize(
                clean_text, tts_backend, conversation_mode, circadian_band, relationship_stage,
                include_fillers=True,
                apply_transforms=format_spec.voice_content_transform_required, rng=rng), None)

    # SC-1: assemble the event sequence.
    orchestrated = _safe(lambda: orchestrate_output(
        clean_text, conversation_mode, circadian_band, format_spec=format_spec,
        micro_plan=micro_plan, thinking_pause_ms=pause_ms, self_edit_plan=self_edit_plan,
        voice_ssml=ssml_document, rng=rng),
        OrchestratedOutput(final_message_text=clean_text, format_spec=format_spec))

    return Layer9Output(
        orchestrated_output=orchestrated, final_message_text=orchestrated.final_message_text,
        format_spec_applied=format_spec, ssml_document=ssml_document, audio_result=audio_result,
        micro_interaction_plan=micro_plan, backchannel_emitted=micro_plan.acknowledgment,
        emotional_prefix_emitted=micro_plan.emotional_prefix,
        self_edit_occurred=self_edit_plan is not None, self_edit_plan=self_edit_plan,
        voice_mode=voice_mode,
        total_orchestration_time_ms=int((time.perf_counter() - start) * 1000))
