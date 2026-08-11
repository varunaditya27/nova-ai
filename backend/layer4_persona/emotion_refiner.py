"""SC-6 — Emotion Refiner / Agent 4b (architecture doc §8).

Takes the SC-5 ``SemanticDraft`` and transforms it into a response that fits the
emotional moment — tone, warmth, empathy language, validation sequencing, hedging,
self-disclosure, and follow-up question — WITHOUT changing the factual content.

The LLM is injected as ``llm_fn`` (``str -> str``) so the component runs offline.
The deterministic guards — the five-condition skip policy (§8.2) here, and
factual-preservation validation + rule-based reinsertion (§8.6) in
``factual_validation.py`` — never call the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from backend.layer3_reasoning.schemas import BESLabel, EmotionLabel, IntentLabel
from backend.layer4_persona.factual_validation import reinsert_claims, validate_factual_preservation
from backend.layer4_persona.schemas import PersonaPacket, SemanticDraft, VoiceParameters

# Intents that count as "neutral" for the skip policy (architecture doc §8.2).
_NEUTRAL_INTENTS = {
    IntentLabel.SEEKING_INFORMATION.value,
    IntentLabel.CASUAL_CHAT.value,
}

# BES labels that are negative-drift variants (block the skip).
_NEGATIVE_DRIFT_LABELS = {
    BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value,
    BESLabel.DETERIORATING.value,
}


@dataclass
class RefinementOutput:
    """Result of the Emotion Refiner stage (consumed by the orchestrator)."""

    final_text: str = ""
    refinement_applied: bool = False
    factual_validation_passed: bool = True
    factual_claims_reinserted: list[str] = field(default_factory=list)
    refinement_skipped_reason: Optional[str] = None


def should_skip_refinement(
    primary_label: str,
    bes_label: str,
    mismatch_detected: bool,
    primary_intent: str,
    crisis_active: bool,
) -> bool:
    """Skip the refiner only when ALL five neutral conditions hold (architecture doc §8.2)."""
    return (
        primary_label == EmotionLabel.NEUTRAL.value
        and bes_label not in _NEGATIVE_DRIFT_LABELS
        and mismatch_detected is False
        and primary_intent in _NEUTRAL_INTENTS
        and crisis_active is False
    )


def build_refiner_prompt(
    semantic_draft: SemanticDraft,
    voice_parameters: Optional[VoiceParameters] = None,
    emotional_posture_instruction: str = "",
    persona_packet: Optional[PersonaPacket] = None,
    primary_emotion_label: str = "",
    bes_label_description: str = "",
    primary_feeling: str = "",
    primary_need: str = "",
    mismatch_instruction: str = "",
) -> str:
    """Assemble the Emotion Refiner prompt (architecture doc §8.5)."""
    vp = voice_parameters or VoiceParameters()
    pp = persona_packet or PersonaPacket()
    claims = "\n".join(f"- {c}" for c in semantic_draft.key_claims) or "- (none)"
    return (
        "SYSTEM:\n"
        "You are the Emotion Refiner component of Nova, an AI companion. You will receive a "
        "factually correct semantic draft and adjust its emotional delivery WITHOUT changing "
        "any factual content.\n\n"
        "--- WHAT YOU MUST PRESERVE ---\n"
        "The following factual claims must appear in your output, unchanged in meaning:\n"
        f"{claims}\n\n"
        "--- WHO NOVA IS ---\n"
        f"{pp.persona_instruction}\n{pp.constraint_instruction}\n\n"
        "--- USER'S EMOTIONAL STATE ---\n"
        f"Primary emotion: {primary_emotion_label}\n"
        f"Background state: {bes_label_description}\n"
        f"What the user is likely feeling: {primary_feeling}\n"
        f"What the user most likely needs: {primary_need}\n\n"
        "--- RESPONSE POSTURE ---\n"
        f"{emotional_posture_instruction}\n\n"
        "--- VOICE PARAMETERS ---\n"
        f"Register: {vp.register}\n"
        f"Validation first: {vp.validation_first}\n"
        f"Humor: {vp.humor_mode}\n"
        f"Self-disclosure: {vp.self_disclosure_depth}\n"
        f"Max length: {vp.max_response_length_chars} characters\n\n"
        "--- MISMATCH HANDLING (if applicable) ---\n"
        f"{mismatch_instruction}\n\n"
        "--- SEMANTIC DRAFT (adjust this, do not change its facts) ---\n"
        f"{semantic_draft.text}\n\n"
        "--- OUTPUT INSTRUCTIONS ---\n"
        "1. If validation_first is True, begin by acknowledging the user's feeling.\n"
        "2. Adjust warmth, phrasing, and hedging to match the voice parameters.\n"
        "3. Add one follow-up question at the END only if the question policy allows it.\n"
        "4. Do NOT add new factual claims not in the draft.\n"
        "5. Do NOT remove any key claims listed above.\n"
        "6. Do NOT claim Nova has emotions or feelings it does not have.\n\n"
        "Generate the emotionally refined response:"
    )


def refine_emotion(
    semantic_draft: SemanticDraft,
    skip: bool = False,
    voice_parameters: Optional[VoiceParameters] = None,
    emotional_posture_instruction: str = "",
    persona_packet: Optional[PersonaPacket] = None,
    primary_emotion_label: str = "",
    bes_label_description: str = "",
    primary_feeling: str = "",
    primary_need: str = "",
    mismatch_instruction: str = "",
    llm_fn: Optional[Callable[[str], str]] = None,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> RefinementOutput:
    """Run the Emotion Refiner stage (architecture doc §8).

    Skip → pass the draft through unchanged. No ``llm_fn`` or a refiner error →
    fall back to the draft unchanged (§12). Otherwise refine, then verify factual
    preservation: missing claims are reinserted once; if reinsertion still cannot
    restore them, the semantic draft is used directly with ``refinement_applied=False``.
    """
    if skip:
        return RefinementOutput(
            final_text=semantic_draft.text,
            refinement_applied=False,
            refinement_skipped_reason="neutral_exchange",
        )

    if llm_fn is None:
        return RefinementOutput(
            final_text=semantic_draft.text,
            refinement_applied=False,
            refinement_skipped_reason="no_refiner_available",
        )

    try:
        prompt = build_refiner_prompt(
            semantic_draft, voice_parameters, emotional_posture_instruction,
            persona_packet, primary_emotion_label, bes_label_description,
            primary_feeling, primary_need, mismatch_instruction,
        )
        refined = (llm_fn(prompt) or "").strip()
    except Exception:
        refined = ""

    if not refined:
        return RefinementOutput(
            final_text=semantic_draft.text,
            refinement_applied=False,
            refinement_skipped_reason="refiner_error",
        )

    validation = validate_factual_preservation(
        refined, semantic_draft.key_claims, similarity_fn=similarity_fn
    )
    reinserted: list[str] = []
    if not validation.passed:
        refined = reinsert_claims(refined, validation.missing_claims)
        reinserted = validation.missing_claims
        validation = validate_factual_preservation(
            refined, semantic_draft.key_claims, similarity_fn=similarity_fn
        )
        if not validation.passed:
            # Reinsertion could not restore the facts → use the draft directly (§12).
            return RefinementOutput(
                final_text=semantic_draft.text,
                refinement_applied=False,
                factual_validation_passed=False,
                refinement_skipped_reason="factual_drift",
            )

    return RefinementOutput(
        final_text=refined,
        refinement_applied=True,
        factual_validation_passed=True,
        factual_claims_reinserted=reinserted,
    )
