"""SC-6 · Context Gate (architecture doc §8.5).

Even well-scored memories should not always fire. The gate modulates the effective recall
score by conversation mode × memory kind: ``EffectiveScore = RecallScore × S(t) × G``.

The table is keyed on Layer 3's canonical conversation modes. Reconciliations vs. the doc:
``casual_small_talk`` → ``casual``; ``crisis_detected`` → ``crisis``; and a ``celebration`` row
(absent from the doc) was added with emotion-forward values consistent with the taxonomy.
"""

from __future__ import annotations

from .schemas import (
    ConversationMode,
    EpisodicMemory,
    IdentityMemory,
    Memory,
    SemanticMemory,
)

# Emotional vs factual episodic split point (by emotional_weight).
EPISODIC_EMOTIONAL_THRESHOLD = 0.4

# Gate table: mode → {memory_kind → gate value} (§8.5).
_GATE: dict[ConversationMode, dict[str, float]] = {
    ConversationMode.CASUAL:               {"episodic_emotional": 0.10, "episodic_factual": 0.20, "semantic": 0.50, "identity": 0.20},
    ConversationMode.EMOTIONAL_SUPPORT:    {"episodic_emotional": 1.00, "episodic_factual": 0.30, "semantic": 0.60, "identity": 0.20},
    ConversationMode.CRISIS:               {"episodic_emotional": 1.00, "episodic_factual": 0.10, "semantic": 0.40, "identity": 0.10},
    ConversationMode.TECHNICAL_DISCUSSION: {"episodic_emotional": 0.10, "episodic_factual": 0.70, "semantic": 0.80, "identity": 0.30},
    ConversationMode.GOAL_PLANNING:        {"episodic_emotional": 0.40, "episodic_factual": 0.70, "semantic": 0.90, "identity": 0.30},
    ConversationMode.SOCIAL_COACHING:      {"episodic_emotional": 0.60, "episodic_factual": 0.50, "semantic": 0.80, "identity": 0.20},
    ConversationMode.LIFE_REVIEW:          {"episodic_emotional": 0.90, "episodic_factual": 0.90, "semantic": 0.70, "identity": 0.30},
    # Reconciliation: celebration was missing from the doc table. Emotion-forward, like
    # emotional_support but with factual recall kept low (the moment, not the record).
    ConversationMode.CELEBRATION:          {"episodic_emotional": 0.90, "episodic_factual": 0.30, "semantic": 0.50, "identity": 0.20},
}

# Neutral fallback if an unknown mode is supplied.
_NEUTRAL = {"episodic_emotional": 1.0, "episodic_factual": 1.0, "semantic": 1.0, "identity": 1.0}


def gate_value(mode: ConversationMode, memory_kind: str) -> float:
    """Gate multiplier for a (mode, memory_kind) pair (§8.5)."""
    return _GATE.get(mode, _NEUTRAL).get(memory_kind, 1.0)


def memory_gate_kind(memory: Memory) -> str:
    """Classify a memory into the gate's kind buckets."""
    if isinstance(memory, EpisodicMemory):
        return (
            "episodic_emotional"
            if memory.emotional_weight >= EPISODIC_EMOTIONAL_THRESHOLD
            else "episodic_factual"
        )
    if isinstance(memory, SemanticMemory):
        return "semantic"
    if isinstance(memory, IdentityMemory):
        return "identity"
    return "semantic"  # pragma: no cover - defensive default
