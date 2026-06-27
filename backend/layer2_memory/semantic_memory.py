"""SC-3 · Semantic memory helpers — confidence + contradiction handling (architecture doc §5.3).

Semantic memories emerge from the FCE consolidating clusters of episodes. They are stable by
design; contradicting evidence must accumulate (scaled by confidence) before deprecation.
"""

from __future__ import annotations

import math
from datetime import datetime

from .schemas import EpisodicMemory, SemanticMemory

# Confidence reduction factor applied per contradiction (§5.3).
CONTRADICTION_CONFIDENCE_PENALTY = 0.15
CONFIDENCE_FLOOR = 0.1


def compute_initial_confidence(cluster_size: int) -> float:
    """Initial confidence for a newly consolidated semantic memory (§9.5).

    confidence = 0.5 + 0.05 × cluster_size, capped at 0.95.
    """
    return min(0.5 + 0.05 * cluster_size, 0.95)


def required_contradictions(confidence: float) -> int:
    """Contradictions needed to deprecate a semantic memory (§5.3).

    ``ceil(2 + confidence × 6)`` — high-confidence facts are harder to overturn. (The doc's
    inline comment "confidence 0.3 → 3" is off by one; the formula yields 4, which is used.)
    """
    return math.ceil(2 + confidence * 6)


def handle_contradiction(
    semantic: SemanticMemory, new_evidence: EpisodicMemory, now: datetime
) -> None:
    """Apply a contradicting episode to a semantic memory in place (§5.3).

    Deprecates (non-destructively) once accumulated contradictions cross the confidence-scaled
    threshold; otherwise reduces confidence proportionally to the evidence strength.
    """
    semantic.contradiction_count += 1

    if semantic.contradiction_count >= required_contradictions(semantic.confidence):
        semantic.is_deprecated = True  # retained in store; surfaces only via the audit tool
        semantic.last_contradicted_at = now
        return

    evidence_strength = new_evidence.importance_score * new_evidence.S_current
    semantic.confidence -= evidence_strength * CONTRADICTION_CONFIDENCE_PENALTY
    semantic.confidence = max(semantic.confidence, CONFIDENCE_FLOOR)
    semantic.last_contradicted_at = now
