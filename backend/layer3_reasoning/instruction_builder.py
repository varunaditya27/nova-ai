"""Layer 3 §9.1 — translate structured classification into plain-language LLM instructions.

Split out of ``packet_builder.py``: these are pure lookup/translation functions, not
sub-component orchestration.
"""

from __future__ import annotations

from backend.layer3_reasoning.schemas import (
    AdviceGate,
    ConversationMode,
    EmpathyHypothesis,
    MismatchResult,
    PrimaryNeed,
    ResponsePacing,
    ResponsePosture,
)

# Plain-language posture instructions for the LLM (architecture doc §9.1).
_POSTURE_INSTRUCTIONS: dict[str, tuple[str, str]] = {
    ResponsePosture.VALIDATE_THEN_HOLD.value: (
        "Acknowledge what the user is feeling fully before anything else. "
        "Do not offer solutions or next steps unless they explicitly ask.",
        "Warm, unhurried, present. Resist the urge to fix."),
    ResponsePosture.VALIDATE_THEN_SOLVE.value: (
        "Begin by validating the user's feeling (1-2 sentences), then transition "
        "to practical help. The validation must come first.",
        "Empathetic then action-oriented. Both matter."),
    ResponsePosture.CELEBRATE.value: (
        "Match the user's energy and celebrate with them. Ask follow-up questions "
        "about what happened. This is their moment.",
        "Enthusiastic, warm, genuinely interested."),
    ResponsePosture.CO_THINK.value: (
        "Think alongside the user rather than directing them. Ask questions more "
        "than making statements. Help them reason, don't reason for them.",
        "Curious, exploratory, non-prescriptive."),
    ResponsePosture.INFORM_WITH_WARMTH.value: (
        "Answer the question accurately and completely. Keep it warm and natural.",
        "Clear, concise, human. Not robotic."),
    ResponsePosture.GENTLE_REDIRECT.value: (
        "Gently steer toward something lighter or more grounding without dismissing "
        "what they raised.",
        "Kind, light, steadying."),
    ResponsePosture.LISTEN_ONLY.value: (
        "Respond minimally. Acknowledge that you've heard them. Do not offer "
        "analysis, advice, or reframing. Just be present.",
        "Quiet, steady, present."),
    ResponsePosture.CRISIS_PROTOCOL.value: (
        "Safety first. See crisis protocol. Do not generate normal response.",
        "Grounded, direct, caring. Resources available."),
}

# Mode → (pacing, thinking-pause ms) (architecture doc §8.3, §9).
_MODE_PACING: dict[str, tuple[str, int]] = {
    ConversationMode.CRISIS.value: (ResponsePacing.IMMEDIATE.value, 0),
    ConversationMode.EMOTIONAL_SUPPORT.value: (ResponsePacing.SLOW.value, 1500),
    ConversationMode.LIFE_REVIEW.value: (ResponsePacing.CONTEMPLATIVE.value, 2500),
    ConversationMode.CELEBRATION.value: (ResponsePacing.NORMAL.value, 300),
}
_DEFAULT_PACING = (ResponsePacing.NORMAL.value, 600)

_GATE_CLOSED_POSTURES = {
    ResponsePosture.CRISIS_PROTOCOL.value,
    ResponsePosture.LISTEN_ONLY.value,
    ResponsePosture.VALIDATE_THEN_HOLD.value,
}
_GATE_OPEN_POSTURES = {
    ResponsePosture.VALIDATE_THEN_SOLVE.value,
    ResponsePosture.INFORM_WITH_WARMTH.value,
}
VALIDATION_NEEDS = {PrimaryNeed.TO_BE_VALIDATED.value, PrimaryNeed.TO_BE_HEARD.value}


def construct_response_instruction(
    hypothesis: EmpathyHypothesis,
    mode: str,
    mismatch: MismatchResult,
) -> tuple[str, str]:
    """Translate posture + mismatch into the LLM-facing instruction pair (architecture doc §9.1)."""
    base, posture = _POSTURE_INSTRUCTIONS.get(
        hypothesis.response_posture, ("Respond naturally.", "Warm and attentive."))
    if mismatch.mismatch_detected and hypothesis.apply_mismatch_posture:
        base = base + " Leave a small opening without probing directly."
    return base, posture


def construct_advice_gate(hypothesis: EmpathyHypothesis, prefers_no_advice: bool) -> str:
    """open / gated / closed advice policy for the Semantic Planner (architecture doc §9)."""
    if hypothesis.advice_withheld or prefers_no_advice \
            or hypothesis.response_posture in _GATE_CLOSED_POSTURES:
        return AdviceGate.CLOSED.value
    if hypothesis.response_posture in _GATE_OPEN_POSTURES:
        return AdviceGate.OPEN.value
    return AdviceGate.GATED.value


def pacing_for_mode(mode: str) -> tuple[str, int]:
    """Layer 9 pacing hint for the conversation mode (architecture doc §9)."""
    return _MODE_PACING.get(mode, _DEFAULT_PACING)
