"""SC-5 deterministic advice detection + gate enforcement (architecture doc §7.6).

Split out of ``semantic_planner.py``: sentence-splitting, claim extraction, and
advice-gate logic never call the LLM, distinct from prompt construction and
orchestration.
"""

from __future__ import annotations

import re

from backend.layer4_persona.schemas import AdviceGate, AdviceGateValidationResult, SemanticDraft

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


def complexity_score(text: str) -> float:
    """0.0–1.0 structural complexity proxy for Layer 9 pacing (§7.5)."""
    words = len(text.split())
    score = min(1.0, words / 120.0)
    if re.search(r"(^|\n)\s*[-*\d]", text):   # list-like structure
        score = min(1.0, score + 0.2)
    return round(score, 3)
