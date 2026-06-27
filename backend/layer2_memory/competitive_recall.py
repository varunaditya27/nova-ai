"""SC-6 · Competitive Recall — softmax, effective score, and the 3-memory cap (§8.4, §8.6).

Candidate memories are scored (recall_scorer), gated (context_gate), and combined into an
effective score. The final selection returns the top-3 by effective score — fewer than 1 feels
forgetful, more than 3 feels omniscient and creepy. Softmax with temperature τ is provided for
optional stochastic variation; selection itself is deterministic top-k by effective score.
"""

from __future__ import annotations

import math

from .schemas import ConversationMode, ScoredMemory

# Maximum memories surfaced per retrieval call (§8.6).
MAX_RECALL = 3

# Softmax temperature per conversation mode (§8.4). Lower τ → sharper, near-deterministic.
_MODE_TEMPERATURE: dict[ConversationMode, float] = {
    ConversationMode.TECHNICAL_DISCUSSION: 0.3,   # factual → near-deterministic
    ConversationMode.CASUAL: 0.5,
    ConversationMode.GOAL_PLANNING: 0.5,
    ConversationMode.EMOTIONAL_SUPPORT: 0.7,      # natural variation
    ConversationMode.CRISIS: 0.7,
    ConversationMode.SOCIAL_COACHING: 0.7,
    ConversationMode.LIFE_REVIEW: 0.7,
    ConversationMode.CELEBRATION: 0.7,
}
DEFAULT_TEMPERATURE = 0.7


def softmax(scores: list[float], tau: float) -> list[float]:
    """Temperature-scaled softmax over scores (§8.4). Empty in → empty out."""
    if not scores:
        return []
    scaled = [s / tau for s in scores]
    m = max(scaled)  # numerical stability
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def effective_score(recall_score: float, s_current: float, gate_value: float) -> float:
    """EffectiveScore = RecallScore × S(t) × G(context, memory_type) (§8.5)."""
    return recall_score * s_current * gate_value


def temperature_for_mode(mode: ConversationMode) -> float:
    """Dynamic recall temperature τ for the conversation mode (§8.4)."""
    return _MODE_TEMPERATURE.get(mode, DEFAULT_TEMPERATURE)


def select_recall(scored: list[ScoredMemory], cap: int = MAX_RECALL) -> list[ScoredMemory]:
    """Top-``cap`` memories by effective score, descending (§8.6).

    Memories fully suppressed by the gate (effective score 0) are dropped — surfacing a
    zero-relevance memory is worse than surfacing nothing.
    """
    live = [s for s in scored if s.effective_score > 0.0]
    live.sort(key=lambda s: s.effective_score, reverse=True)
    return live[:cap]
