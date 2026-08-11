"""SC-5 — Semantic Planner / Agent 4a (architecture doc §7).

Generates the factual, task-complete, logically coherent *content* of the response.
It is deliberately NOT responsible for emotional tone, warmth, empathy depth, or
register — those are exclusively the Emotion Refiner's (SC-6) domain. Separating the
passes lets each be constrained, optimized, and evaluated independently (§14.2).

The LLM itself is injected as ``llm_fn`` (a callable ``str -> str``) so the whole
component runs and tests offline. The deterministic steps — key-claim extraction,
advice detection, advice-gate validation, and rule-based advice stripping
(``advice_gate.py``) — never call the LLM (§7.6).
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer4_persona.advice_gate import (
    complexity_score,
    detect_advice,
    extract_key_claims,
    split_sentences,
    strip_advice,
    validate_advice_gate,
)
from backend.layer4_persona.schemas import AdviceGate, PersonaPacket, SemanticDraft

__all__ = [
    "build_planner_prompt",
    "detect_advice",
    "extract_key_claims",
    "generate_semantic_draft",
    "split_sentences",
    "strip_advice",
    "validate_advice_gate",
]


def _format_memories(recalled_memories) -> str:
    if not recalled_memories:
        return "(no specific memories recalled — do not invent or imply any)"
    lines = []
    for m in recalled_memories:
        label = getattr(m, "fuzzy_temporal_label", "") or "previously"
        # EpisodicMemory's content field is ``summary``, not ``content`` — falling back to
        # str(m) here would dump the raw ScoredMemory repr (embedding floats, recall_score)
        # into the LLM prompt, violating the "no raw scores to LLM" invariant.
        text = getattr(getattr(m, "memory", None), "summary", "")
        if text:
            lines.append(f"- ({label}) {text}")
    return "\n".join(lines) or "(no specific memories recalled — do not invent or imply any)"


def build_planner_prompt(
    user_message: str,
    persona_packet: Optional[PersonaPacket] = None,
    advice_gate: str = AdviceGate.OPEN.value,
    response_instruction: str = "",
    recalled_memories=None,
    max_response_length_chars: int = 1200,
    circadian_band: str = "afternoon",
) -> str:
    """Assemble the Semantic Planner prompt (architecture doc §7.4)."""
    pp = persona_packet or PersonaPacket()
    return (
        "SYSTEM:\n"
        "You are the Semantic Planner component of Nova, an AI companion. Generate a "
        "factually accurate, contextually grounded response draft. Your output will be "
        "refined by a separate Emotion Refiner stage. Therefore:\n"
        "- DO generate accurate, complete content addressing the user's request\n"
        "- DO ground the response in the provided memory context\n"
        "- DO respect the persona constraints and advice gate below\n"
        "- DO NOT add emotional language, warmth phrases, or empathy expressions\n"
        "- DO NOT add follow-up questions — that is the Refiner's job\n"
        f"- DO NOT exceed {max_response_length_chars} characters\n\n"
        "--- PERSONA CONSTRAINTS ---\n"
        f"{pp.persona_instruction}\n{pp.constraint_instruction}\n{pp.memory_reference_policy}\n\n"
        "--- ADVICE GATE ---\n"
        f"Advice gate: {advice_gate}\n"
        '- "open": freely offer advice and recommendations\n'
        '- "gated": only offer advice if the user explicitly asked; otherwise hold back\n'
        '- "closed": do not offer advice, recommendations, or problem-solving content\n\n'
        "--- MEMORY CONTEXT ---\n"
        f"{_format_memories(recalled_memories)}\n\n"
        "--- TEMPORAL CONTEXT ---\n"
        f"Current time band: {circadian_band}\n\n"
        "--- RESPONSE INSTRUCTION ---\n"
        f"{response_instruction}\n\n"
        "--- USER MESSAGE ---\n"
        f"{user_message}\n\n"
        "Generate the semantic draft response:"
    )


# Graceful, non-empty fallback when the planner LLM is absent or fails (§12).
_FALLBACK_DRAFT_TEXT = "Here's what I can tell you."


def generate_semantic_draft(
    user_message: str,
    persona_packet: Optional[PersonaPacket] = None,
    advice_gate: str = AdviceGate.OPEN.value,
    prefers_no_advice: bool = False,
    explicitly_asked_for_advice: bool = False,
    response_instruction: str = "",
    recalled_memories=None,
    max_response_length_chars: int = 1200,
    circadian_band: str = "afternoon",
    llm_fn: Optional[Callable[[str], str]] = None,
) -> SemanticDraft:
    """Produce the SC-5 ``SemanticDraft`` (architecture doc §7).

    Calls the injected ``llm_fn`` with the assembled prompt; on absence or failure,
    falls back to a non-empty placeholder draft (§12 hard rule). After generation, the
    advice gate is enforced deterministically: a violating draft has its advice stripped
    (no extra LLM call). ``prefers_no_advice`` tightens an ``open`` gate to behave as
    ``gated`` for this turn.
    """
    text = ""
    if llm_fn is not None:
        try:
            prompt = build_planner_prompt(
                user_message, persona_packet, advice_gate, response_instruction,
                recalled_memories, max_response_length_chars, circadian_band,
            )
            text = (llm_fn(prompt) or "").strip()
        except Exception:
            text = ""
    if not text:
        text = _FALLBACK_DRAFT_TEXT

    draft = SemanticDraft(
        text=text,
        key_claims=extract_key_claims(text),
        memory_references_used=[
            getattr(getattr(m, "memory", None), "memory_id", "") and
            str(getattr(getattr(m, "memory", None), "memory_id", ""))
            for m in (recalled_memories or [])
        ],
        advice_included=detect_advice(text),
        word_count=len(text.split()),
        complexity_score=complexity_score(text),
    )
    draft.memory_references_used = [r for r in draft.memory_references_used if r]

    # Honor an explicit "no advice" preference by tightening the gate.
    effective_gate = advice_gate
    if prefers_no_advice and advice_gate == AdviceGate.OPEN.value:
        effective_gate = AdviceGate.GATED.value

    validation = validate_advice_gate(draft, effective_gate, explicitly_asked_for_advice)
    if not validation.passed and validation.action == "strip_advice":
        draft.text = strip_advice(draft.text) or _FALLBACK_DRAFT_TEXT
        draft.advice_included = detect_advice(draft.text)
        draft.key_claims = extract_key_claims(draft.text)
        draft.word_count = len(draft.text.split())

    return draft
