"""SC-5 — Semantic Planner / Agent 4a (architecture doc §7).

Generates the factual, task-complete, logically coherent *content* of the response.
It is deliberately NOT responsible for emotional tone, warmth, empathy depth, or
register — those are exclusively the Emotion Refiner's (SC-6) domain. Separating the
passes lets each be constrained, optimized, and evaluated independently (§14.2).

The LLM itself is injected as ``llm_fn`` (a callable ``str -> str``) so the whole
component runs and tests offline. The deterministic steps — key-claim extraction,
advice detection, advice-gate validation, and rule-based advice stripping — never
call the LLM (§7.6).
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from backend.layer4_persona.schemas import (
    AdviceGate,
    AdviceGateValidationResult,
    PersonaPacket,
    SemanticDraft,
)

# Advice / recommendation patterns (architecture doc §7.6). Used both to flag a
# draft (``advice_included``) and to strip advice sentences when the gate forbids it.
_ADVICE_PATTERNS = [
    r"\byou should\b", r"\byou could\b", r"\byou might want to\b", r"\byou ought to\b",
    r"\bi recommend\b", r"\bi'd recommend\b", r"\bi suggest\b", r"\bi'd suggest\b",
    r"\btry to\b", r"\btry \w+ing\b", r"\bconsider \w+ing\b", r"\bhave you considered\b",
    r"\bwhat if you\b", r"\bmaybe you\b", r"\bwhy not\b", r"\bmy advice\b",
]
_ADVICE_RE = re.compile("|".join(_ADVICE_PATTERNS), re.IGNORECASE)

# Sentence splitter that keeps the terminator so we can tell questions from statements.
_SENTENCE_RE = re.compile(r"[^.!?]*[.!?]|[^.!?]+$")


def split_sentences(text: str) -> list[str]:
    """Split text into trimmed, non-empty sentences (terminator preserved)."""
    return [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip()]


def extract_key_claims(text: str) -> list[str]:
    """Extract declarative factual claims for post-refinement validation (§7.5).

    Questions and very short fragments are excluded — they carry no factual claim to
    preserve through the Emotion Refiner.
    """
    claims = []
    for sentence in split_sentences(text):
        if sentence.endswith("?"):
            continue
        if len(sentence.split()) < 3:
            continue
        claims.append(sentence)
    return claims


def detect_advice(text: str) -> bool:
    """True if the text contains advice / recommendation content (§7.6)."""
    return bool(_ADVICE_RE.search(text or ""))


def strip_advice(text: str) -> str:
    """Remove advice sentences via rule-based sentence removal — no LLM call (§7.6)."""
    kept = [s for s in split_sentences(text) if not detect_advice(s)]
    return " ".join(kept).strip()


def validate_advice_gate(
    draft: SemanticDraft,
    advice_gate: str,
    explicitly_asked: bool = False,
) -> AdviceGateValidationResult:
    """Deterministic advice-gate compliance check (architecture doc §7.6)."""
    if advice_gate == AdviceGate.CLOSED.value and draft.advice_included:
        return AdviceGateValidationResult(
            passed=False,
            violation="Draft includes advice content but advice gate is closed",
            action="strip_advice",
        )
    if advice_gate == AdviceGate.GATED.value and draft.advice_included and not explicitly_asked:
        return AdviceGateValidationResult(
            passed=False,
            violation="Draft includes advice but the user did not explicitly ask",
            action="strip_advice",
        )
    return AdviceGateValidationResult(passed=True)


def _complexity_score(text: str) -> float:
    """0.0–1.0 structural complexity proxy for Layer 9 pacing (§7.5)."""
    words = len(text.split())
    score = min(1.0, words / 120.0)
    if re.search(r"(^|\n)\s*[-*\d]", text):   # list-like structure
        score = min(1.0, score + 0.2)
    return round(score, 3)


def _format_memories(recalled_memories) -> str:
    if not recalled_memories:
        return "(no specific memories recalled — do not invent or imply any)"
    lines = []
    for m in recalled_memories:
        label = getattr(m, "fuzzy_temporal_label", "") or "previously"
        text = getattr(getattr(m, "memory", None), "content", "") or str(m)
        lines.append(f"- ({label}) {text}")
    return "\n".join(lines)


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
        complexity_score=_complexity_score(text),
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
