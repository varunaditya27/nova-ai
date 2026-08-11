"""Layer 3 orchestrator — assembles the EmotionIntentPacket (architecture doc §9, §12).

Runs the six sub-components in order (SC-1..SC-4 are independent, SC-5 synthesises them,
SC-6 resolves the mode), translates the structured result into the plain-language
instructions the LLM will actually receive (§9.1), and guarantees the two hard rules of
§12: a crisis alert is emitted to Layer 11 (Safety Agent) *before* anything that can fail, and
Layer 3 always emits a packet — a degraded packet beats no packet.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from backend.layer3_reasoning._safety_helpers import emit_alert, safe
from backend.layer3_reasoning.background_state import compute_background_state
from backend.layer3_reasoning.emotion_classifier import classify_emotion, heuristic_prefilter
from backend.layer3_reasoning.empathy_hypothesis import generate_empathy_hypothesis
from backend.layer3_reasoning.instruction_builder import (
    VALIDATION_NEEDS,
    construct_advice_gate,
    construct_response_instruction,
    pacing_for_mode,
)
from backend.layer3_reasoning.intent_classifier import classify_intent, rule_classify
from backend.layer3_reasoning.mismatch_detector import detect_mismatch
from backend.layer3_reasoning.mode_resolver import resolve_conversation_mode
from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    ClassificationMethod,
    ConversationMode,
    CrisisAlert,
    EmotionClassification,
    EmotionLabel,
    EmpathyHypothesis,
    EmotionIntentPacket,
    IntentClassification,
    IntentLabel,
    LLMClassificationOutput,
    MismatchResult,
)

CRISIS_THRESHOLD = 0.65


def build_emotion_intent_packet(
    message: str,
    *,
    implicit_intensity: float = 0.0,
    circadian_band: str = "afternoon",
    composite_prior: float = 0.0,
    prior_confidence: float = 0.0,
    prosody_estimate=None,
    signal_mismatch_flag: bool = False,
    episodic_memories=None,
    active_stressors=None,
    psychological_model=None,
    relationship_depth: float = 0.0,
    advice_frustration_count: int = 0,
    llm_fn: Optional[Callable[[str], LLMClassificationOutput]] = None,
    alert_fn: Optional[Callable[[CrisisAlert], None]] = None,
    now=None,
) -> EmotionIntentPacket:
    """Run all six sub-components and assemble the read-only packet (architecture doc §9)."""
    start = time.perf_counter()
    episodic_memories = episodic_memories or []
    active_stressors = active_stressors or []

    # ── Crisis fast path: emit the alert before any fallible work (§3.6, §12) ──
    crisis_emitted = False
    pre = safe(
        lambda: heuristic_prefilter(message, implicit_intensity, circadian_band, prosody_estimate),
        None)
    if (alert_fn is not None and pre is not None and pre.crisis_flag
            and pre.crisis_confidence > CRISIS_THRESHOLD):
        emit_alert(alert_fn, pre, message, source="layer3_heuristic")
        crisis_emitted = True

    # ── Shared SC-1/SC-3 LLM call (architecture doc §14.2) ────────────────────
    # One fast small-model call serves both classifiers, not two independent inferences: fire it
    # exactly when either half would otherwise need its own (emotion's heuristic didn't resolve
    # to pure-neutral, or intent's rule table didn't confidently match) and hand the same parsed
    # result to both. Each classifier still runs its own skip/degrade logic unchanged (via
    # `llm_output=`); this only removes the duplicate network round trip.
    emotion_needs_llm = not (pre is not None and pre.primary_label == EmotionLabel.NEUTRAL.value)
    intent_rule = safe(lambda: rule_classify(message), None)
    intent_needs_llm = intent_rule is None
    shared_llm_output = None
    if llm_fn is not None and (emotion_needs_llm or intent_needs_llm):
        shared_llm_output = safe(lambda: llm_fn(message), None)

    # ── SC-1 Primary Emotion ──────────────────────────────────────────────────
    emotion = safe(
        lambda: classify_emotion(
            message, implicit_intensity=implicit_intensity, circadian_band=circadian_band,
            composite_prior=composite_prior, prior_confidence=prior_confidence,
            prosody_estimate=prosody_estimate, llm_output=shared_llm_output,
            llm_fn=None if shared_llm_output is not None else llm_fn),
        pre or EmotionClassification(
            primary_label=EmotionLabel.NEUTRAL.value, confidence=0.5,
            classification_method=ClassificationMethod.HEURISTIC_ONLY.value))
    llm_made = emotion.classification_method in (
        ClassificationMethod.LLM_ONLY.value, ClassificationMethod.LLM_PLUS_PRIOR.value)

    # LLM-detected crisis that the heuristic missed.
    if (alert_fn is not None and not crisis_emitted and emotion.crisis_flag
            and emotion.crisis_confidence > CRISIS_THRESHOLD):
        emit_alert(alert_fn, emotion, message, source="layer3_llm")
        crisis_emitted = True

    crisis_active = emotion.crisis_flag and emotion.crisis_confidence > CRISIS_THRESHOLD

    # ── SC-2 Background Emotional State ───────────────────────────────────────
    bes = safe(
        lambda: compute_background_state(
            episodic_memories, active_stressors=active_stressors,
            psychological_model=psychological_model, now=now),
        BackgroundEmotionalState())

    # ── SC-3 Intent ───────────────────────────────────────────────────────────
    intent = safe(
        lambda: classify_intent(
            message, llm_output=shared_llm_output,
            llm_fn=None if shared_llm_output is not None else llm_fn,
            advice_frustration_count=advice_frustration_count),
        IntentClassification(primary_intent=IntentLabel.CASUAL_CHAT.value))

    # ── SC-4 Mismatch ─────────────────────────────────────────────────────────
    mismatch = safe(
        lambda: detect_mismatch(
            emotion, composite_prior, implicit_intensity, prosody_estimate,
            signal_mismatch_flag, message, bes, relationship_depth=relationship_depth),
        MismatchResult(mismatch_detected=False))

    # ── SC-5 Empathy Hypothesis ───────────────────────────────────────────────
    hypothesis = safe(
        lambda: generate_empathy_hypothesis(
            emotion, bes, intent, mismatch, relationship_depth, psychological_model),
        EmpathyHypothesis(is_crisis=crisis_active))

    # ── SC-6 Conversation Mode ────────────────────────────────────────────────
    mode = safe(
        lambda: resolve_conversation_mode(emotion, bes, intent, mismatch),
        ConversationMode.CASUAL.value)
    if crisis_active:
        mode = ConversationMode.CRISIS.value  # crisis is unconditional (§8.2)

    # ── Translate to LLM-facing instructions (§9.1) ───────────────────────────
    response_instruction, posture_instruction = construct_response_instruction(
        hypothesis, mode, mismatch)
    advice_gate = construct_advice_gate(hypothesis, intent.prefers_no_advice)
    pacing, thinking_pause = pacing_for_mode(mode)

    needs_validation_first = (
        intent.needs_validation or hypothesis.primary_need in VALIDATION_NEEDS)
    validation_instruction = (
        "Explicitly affirm that what they feel makes sense before doing anything else."
        if needs_validation_first else None)

    confidence_overall = min(
        emotion.confidence if emotion.confidence > 0 else 1.0,
        intent.intent_confidence if intent.intent_confidence > 0 else 1.0,
    )

    latency_ms = int((time.perf_counter() - start) * 1000)

    return EmotionIntentPacket(
        primary_emotion=emotion,
        background_state=bes,
        intent=intent,
        topic_domain=intent.topic_domain,
        prefers_no_advice=intent.prefers_no_advice,
        needs_validation_first=needs_validation_first,
        mismatch=mismatch,
        mismatch_response_posture=mismatch.mismatch_response_posture,
        empathy_hypothesis=hypothesis,
        conversation_mode=mode,
        crisis_active=crisis_active,
        crisis_type=emotion.crisis_type,
        crisis_confidence=emotion.crisis_confidence,
        response_instruction=response_instruction,
        emotional_posture_instruction=posture_instruction,
        validation_instruction=validation_instruction,
        advice_gate=advice_gate,
        suggested_response_pacing=pacing,
        suggested_thinking_pause_ms=thinking_pause,
        classification_latency_ms=latency_ms,
        llm_call_made=llm_made,
        classification_confidence_overall=confidence_overall,
    )
