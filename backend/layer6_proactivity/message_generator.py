"""SC-4 — Proactive Message Generator (architecture doc §6).

The only LLM call in Layer 6. Takes the approved item + its ClassifiedInitiative, loads
context, and generates the outreach message. The message must feel natural (like a friend
who thought of you), be grounded in something specific, and leave the user fully in control.

The LLM is injected as ``llm_fn`` so the component runs offline. After generation, three
deterministic checks (§6.4) run; a failing message is regenerated with the issue appended
to the prompt, up to 2 attempts. Per the §11 hard rule, there is NO pre-written fallback —
if generation fails, nothing is sent (the caller defers the item).
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer6_proactivity.schemas import (
    ClassifiedInitiative,
    ProactiveContext,
    ProactiveDeliveryPayload,
    ProactiveItem,
    ProactiveItemType,
    ProactiveValidationResult,
)

# Phrases that make a proactive message feel algorithmic (architecture doc §6.4).
ROBOT_PHRASES = [
    "i noticed in our conversation",
    "according to what you told me",
    "as per our previous",
    "i wanted to check in",
    "just checking in",
    "reach out",
    "i'm here for you",
]

# Phrases that presume the outcome of a pending event (architecture doc §6.4).
ASSUMPTION_PHRASES = [
    "i'm sure it went well",
    "hope it went great",
    "bet you aced it",
    "you must have done",
]

_OUTCOME_SENSITIVE_TYPES = {
    ProactiveItemType.THREAD_FOLLOW_UP.value,
    ProactiveItemType.UPCOMING_DATE_REMINDER.value,
}

_MAX_REGEN_ATTEMPTS = 2


def validate_proactive_message(
    message_text: str,
    classified: ClassifiedInitiative,
    item: ProactiveItem,
) -> ProactiveValidationResult:
    """Three deterministic quality checks before delivery (architecture doc §6.4)."""
    low = message_text.lower()

    if len(message_text) > classified.max_length_chars:
        return ProactiveValidationResult(passed=False, issue="over_length",
                                         action="truncate_or_regenerate")

    for phrase in ROBOT_PHRASES:
        if phrase in low:
            return ProactiveValidationResult(passed=False, issue=f"robot_phrase: {phrase}",
                                             action="regenerate")

    if message_text.count("?") > 2:
        return ProactiveValidationResult(passed=False, issue="too_many_questions",
                                         action="regenerate")

    if item.item_type in _OUTCOME_SENSITIVE_TYPES:
        for phrase in ASSUMPTION_PHRASES:
            if phrase in low:
                return ProactiveValidationResult(passed=False, issue="assumes_outcome",
                                                 action="regenerate")

    return ProactiveValidationResult(passed=True)


def build_proactive_prompt(
    item: ProactiveItem,
    classified: ClassifiedInitiative,
    context: ProactiveContext,
    extra_constraint: str = "",
) -> str:
    """Assemble the proactive-message prompt (architecture doc §6.3)."""
    sources = "\n".join(context.source_memory_summaries) or item.content_basis
    if context.source_thread_summary:
        sources += f"\n{context.source_thread_summary}"
    topics = ", ".join(context.prior_proactive_topics) or "(none)"
    extra = f"\nADDITIONAL CONSTRAINT (previous attempt failed): {extra_constraint}" if extra_constraint else ""
    return (
        f"SYSTEM:\nYou are Nova — {context.persona_instruction}\n\n"
        "Generate a single proactive message to send to the user. It is sent WITHOUT being "
        "prompted — it should feel like a friend who remembered something and thought of them.\n\n"
        "--- WHAT THIS MESSAGE IS BASED ON ---\n"
        f"{sources}\n\n"
        "--- USER CONTEXT ---\n"
        f"Current life context: {context.current_life_context}\n"
        f"Emotional trajectory: {context.bes_trend_description}\n\n"
        "--- INITIATIVE TYPE AND REGISTER ---\n"
        f"Initiative type: {classified.initiative_type}\n"
        f"Emotional register: {classified.emotional_register}\n"
        f"Content framing: {classified.content_framing}\n"
        f"Reference depth: {classified.reference_depth}\n"
        f"Opening posture: {classified.opening_posture}\n\n"
        "--- VOICE PARAMETERS ---\n"
        f"{context.voice_parameters_summary}\n"
        f"Max length: {classified.max_length_chars} characters\n\n"
        "--- CRITICAL CONSTRAINTS ---\n"
        "1. The user did NOT write first — it must feel natural, not algorithmic.\n"
        "2. Do not express urgency or demand a response.\n"
        '3. Do not use "reach out", "just checking in", or "I wanted to check in".\n'
        f"4. End with at most one natural question if include_question is {classified.include_question}.\n"
        "5. Do not assume the outcome of any pending event.\n"
        f"6. Maximum length: {classified.max_length_chars} characters. Shorter is better."
        f"{extra}\n\n"
        "--- TOPICS TO AVOID (already covered recently) ---\n"
        f"{topics}\n\n"
        "Generate the proactive message:"
    )


def generate_proactive_message(
    item: ProactiveItem,
    classified: ClassifiedInitiative,
    context: ProactiveContext,
    user_id: str = "",
    llm_fn: Optional[Callable[[str], str]] = None,
    max_attempts: int = _MAX_REGEN_ATTEMPTS,
    now: Optional[datetime] = None,
) -> Optional[ProactiveDeliveryPayload]:
    """Generate + validate the proactive message (architecture doc §6).

    Returns a delivery payload on success, or ``None`` if generation/validation fails after
    ``max_attempts`` — there is no fallback message (§11). The injected ``llm_fn`` keeps the
    component offline-testable.
    """
    if llm_fn is None:
        return None

    now = now or datetime.utcnow()
    extra_constraint = ""
    for _ in range(max_attempts):
        prompt = build_proactive_prompt(item, classified, context, extra_constraint)
        try:
            text = (llm_fn(prompt) or "").strip()
        except Exception:
            return None
        if not text:
            continue
        result = validate_proactive_message(text, classified, item)
        if result.passed:
            return ProactiveDeliveryPayload(
                user_id=user_id,
                message_text=text,
                item_id=item.item_id,
                send_at=now,
                allow_reply=True,
                tracking_enabled=True,
            )
        extra_constraint = f"Avoid this problem: {result.issue}."

    return None
