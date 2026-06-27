"""SC-6 · Recall Scoring Engine — the four-component recall score (architecture doc §8.2).

Memory retrieval is a competition governed by four simultaneously weighted signals:
semantic similarity, emotional congruence (mood-congruent recall), temporal recency, and
importance × current vitality. Pure arithmetic, CPU-only (§16).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .embedding import cosine_similarity
from .schemas import EmotionVector, EpisodicMemory, Memory, SemanticMemory

# Emotional-distance sharpness (§8.2 component 2).
LAMBDA_E = 2.0


@dataclass(frozen=True)
class RecallWeights:
    """The α/β/γ/δ recall weights. Must sum to 1.0 (§8.2)."""

    alpha: float = 0.40   # semantic
    beta: float = 0.30    # emotional (mood-congruent recall — first-class, §18.3)
    gamma: float = 0.20   # temporal
    delta: float = 0.10   # importance


DEFAULT_WEIGHTS = RecallWeights()


def semantic_component(memory_embedding: list[float], query_embedding: list[float]) -> float:
    """Component 1 — cosine similarity between query and memory embeddings (§8.2)."""
    return cosine_similarity(memory_embedding, query_embedding)


def emotional_component(
    memory_emotion: EmotionVector, current_emotion: EmotionVector, lambda_e: float = LAMBDA_E
) -> float:
    """Component 2 — mood-congruent recall: exp(−λ_e·‖m − e‖²) over valence/arousal (§8.2)."""
    dv = memory_emotion.valence - current_emotion.valence
    da = memory_emotion.arousal - current_emotion.arousal
    dist_sq = dv * dv + da * da
    return math.exp(-lambda_e * dist_sq)


def temporal_component(decay_rate: float, t_days: float) -> float:
    """Component 3 — exp(−decay_rate·t). Recent memories score higher; importance slows decay (§8.2)."""
    return math.exp(-decay_rate * t_days)


def importance_component(importance_score: float, S_current: float) -> float:
    """Component 4 — historical significance × current vitality (§8.2)."""
    return importance_score * S_current


def _days_between(later: datetime, earlier: Optional[datetime]) -> float:
    if earlier is None:
        return 0.0
    return max(0.0, (later - earlier).total_seconds() / 86400.0)


def score_memory(
    memory: Memory,
    query_embedding: list[float],
    current_emotion: EmotionVector,
    now: datetime,
    weights: RecallWeights = DEFAULT_WEIGHTS,
) -> tuple[float, dict]:
    """Compute the weighted recall score and per-component breakdown for a memory (§8.2).

    Works for both episodic and semantic memories. Semantic memories have no emotional state
    (neutral congruence) and use ``confidence`` as their importance signal.
    """
    semantic = semantic_component(memory.embedding, query_embedding)

    if isinstance(memory, EpisodicMemory):
        emotional = emotional_component(memory.emotion_vector, current_emotion)
        temporal = temporal_component(memory.decay_rate, _days_between(now, memory.created_at))
        importance = importance_component(memory.importance_score, memory.S_current)
    elif isinstance(memory, SemanticMemory):
        emotional = emotional_component(EmotionVector(), current_emotion)  # neutral
        temporal = temporal_component(memory.decay_rate, _days_between(now, memory.last_confirmed_at))
        importance = importance_component(memory.confidence, memory.S_current)
    else:  # pragma: no cover - defensive
        emotional = temporal = importance = 0.0

    components = {
        "semantic": semantic,
        "emotional": emotional,
        "temporal": temporal,
        "importance": importance,
    }
    score = (
        weights.alpha * semantic
        + weights.beta * emotional
        + weights.gamma * temporal
        + weights.delta * importance
    )
    return score, components
