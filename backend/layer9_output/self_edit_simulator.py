"""SC-1 — Self-Edit Simulator (architecture doc §3.4).

Plans a visible mid-typing deletion and revision when Layer 4's emotion-refined ``final_response``
diverged from the ``semantic_draft`` — Nova appears to type a phrase from the draft, reconsider,
delete it, and continue. Disabled in crisis/task/technical modes and with strangers. Probability
scales with complexity. Randomness is injected (``rng``) for deterministic testing.
"""

from __future__ import annotations

import random as _random
from typing import Optional

from backend.layer9_output.schemas import SelfEditPlan

_DISABLED_MODES = {"crisis_support", "task_help", "technical"}
_DISABLED_STAGES = {"stranger"}


def _self_edit_probability(complexity_score: float) -> float:
    if complexity_score < 0.4:
        return 0.10
    if complexity_score < 0.65:
        return 0.25
    return 0.40


def plan_self_edit(
    semantic_draft: str,
    final_response: str,
    complexity_score: float,
    relationship_stage: str,
    conversation_mode: str,
    rng=_random,
) -> Optional[SelfEditPlan]:
    """Return a SelfEditPlan if self-editing should be simulated, else None (doc §3.4)."""
    if conversation_mode in _DISABLED_MODES or relationship_stage in _DISABLED_STAGES:
        return None
    if rng.random() > _self_edit_probability(complexity_score):
        return None

    # Find a clause-length segment present in the draft but changed out of the final.
    draft_clauses = [c.strip() for c in semantic_draft.replace(",", ".").split(".")
                     if len(c.strip()) > 20]
    final_lower = final_response.lower()
    for clause in draft_clauses:
        if clause.lower()[:25] not in final_lower:
            insert_ratio = rng.uniform(0.15, 0.45)
            return SelfEditPlan(
                phrase_to_show_then_delete=clause[:40] + ("..." if len(clause) > 40 else ""),
                insert_after_chars=int(len(final_response) * insert_ratio),
                deletion_pause_ms=rng.randint(400, 800),
                resume_pause_ms=rng.randint(300, 600))
    return None
