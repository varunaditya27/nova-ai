"""SC-6 post-refinement factual-preservation validation (architecture doc §8.6).

Split out of ``emotion_refiner.py``: deterministic claim-coverage checking, distinct
from prompt construction and orchestration.

Factual preservation default: the doc specifies embedding cosine ≥ 0.65 (§8.6); the
offline default here uses claim-token *coverage* (recall of the claim's tokens by the
best refined sentence) with the same 0.65 threshold. A real embedding ``similarity_fn``
can be injected to match the production behavior exactly.
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer4_persona.schemas import FactualValidationResult
from backend.layer4_persona.semantic_planner import split_sentences

_COVERAGE_THRESHOLD = 0.65


def _tokens(text: str) -> set:
    return {t.strip(".,!?'\"").lower() for t in text.split() if t.strip(".,!?'\"")}


def _coverage(claim: str, sentence: str) -> float:
    """Fraction of the claim's tokens covered by ``sentence`` (0.0–1.0)."""
    claim_tokens = _tokens(claim)
    if not claim_tokens:
        return 1.0
    return len(claim_tokens & _tokens(sentence)) / len(claim_tokens)


def claim_present(
    claim: str,
    refined_text: str,
    threshold: float = _COVERAGE_THRESHOLD,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> bool:
    """True if ``claim`` is adequately present in ``refined_text`` (architecture doc §8.6)."""
    sim = similarity_fn or _coverage
    sentences = split_sentences(refined_text) or [refined_text]
    best = max((sim(claim, s) for s in sentences), default=0.0)
    return best >= threshold


def validate_factual_preservation(
    refined_text: str,
    key_claims: list[str],
    threshold: float = _COVERAGE_THRESHOLD,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> FactualValidationResult:
    """Check that every key claim survives the refinement (architecture doc §8.6)."""
    missing = [
        claim for claim in key_claims
        if not claim_present(claim, refined_text, threshold, similarity_fn)
    ]
    if missing:
        return FactualValidationResult(passed=False, missing_claims=missing, action="reinsert")
    return FactualValidationResult(passed=True)


def reinsert_claims(refined_text: str, missing_claims: list[str]) -> str:
    """Append dropped factual claims with a soft transition — no LLM call (§8.6)."""
    if not missing_claims:
        return refined_text
    addendum = " ".join(c.rstrip(".") + "." for c in missing_claims)
    sep = " " if refined_text and not refined_text.endswith((" ", "\n")) else ""
    return f"{refined_text}{sep}To be clear: {addendum}".strip()
