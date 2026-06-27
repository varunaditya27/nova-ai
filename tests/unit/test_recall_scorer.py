"""Tests for SC-6 four-component recall score (architecture doc §8.2)."""

import math
from datetime import datetime, timedelta

from backend.layer2_memory import recall_scorer as rs
from backend.layer2_memory.schemas import EmotionVector, EpisodicMemory

NOW = datetime(2026, 6, 26, 12, 0, 0)


def test_semantic_component_is_cosine():
    assert rs.semantic_component([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert rs.semantic_component([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_emotional_component_identical_state_is_one():
    e = EmotionVector(valence=-0.5, arousal=0.7)
    assert rs.emotional_component(e, e) == 1.0


def test_emotional_component_decays_with_distance():
    near = rs.emotional_component(EmotionVector(valence=-0.5, arousal=0.6),
                                  EmotionVector(valence=-0.4, arousal=0.6))
    far = rs.emotional_component(EmotionVector(valence=0.8, arousal=0.1),
                                 EmotionVector(valence=-0.8, arousal=0.9))
    assert near > far
    # exact: ||Δ||² = 0.01, λ_e=2 → exp(-0.02)
    assert math.isclose(near, math.exp(-0.02), rel_tol=1e-9)


def test_temporal_component_recent_is_higher():
    assert rs.temporal_component(decay_rate=0.05, t_days=0) == 1.0
    assert rs.temporal_component(0.05, 30) < rs.temporal_component(0.05, 1)


def test_importance_component_is_significance_times_vitality():
    assert rs.importance_component(importance_score=0.8, S_current=0.5) == 0.4


def test_full_recall_score_perfect_match_is_one():
    q = [1.0, 0.0, 0.0]
    e = EmotionVector(valence=-0.5, arousal=0.7)
    mem = EpisodicMemory(
        embedding=[1.0, 0.0, 0.0], emotion_vector=e, decay_rate=0.0,
        created_at=NOW, importance_score=1.0, S_current=1.0,
    )
    score, components = rs.score_memory(mem, q, e, NOW)
    assert math.isclose(score, 1.0, rel_tol=1e-9)
    assert set(components) == {"semantic", "emotional", "temporal", "importance"}


def test_recall_score_uses_default_weights():
    q = [1.0, 0.0]
    e = EmotionVector()
    mem = EpisodicMemory(embedding=[0.0, 1.0], emotion_vector=e, decay_rate=0.0,
                         created_at=NOW, importance_score=0.0, S_current=0.0)
    # semantic=0, emotional=1 (identical neutral), temporal=1, importance=0
    score, comp = rs.score_memory(mem, q, e, NOW)
    # 0.40*0 + 0.30*1 + 0.20*1 + 0.10*0 = 0.5
    assert math.isclose(score, 0.5, rel_tol=1e-9)


def test_weights_sum_to_one():
    w = rs.DEFAULT_WEIGHTS
    assert math.isclose(w.alpha + w.beta + w.gamma + w.delta, 1.0, rel_tol=1e-9)
    assert (w.alpha, w.beta, w.gamma, w.delta) == (0.40, 0.30, 0.20, 0.10)


def test_temporal_uses_elapsed_days_from_created_at():
    q = [1.0]
    e = EmotionVector()
    mem = EpisodicMemory(embedding=[1.0], emotion_vector=e, decay_rate=0.1,
                         created_at=NOW - timedelta(days=10), importance_score=0.0,
                         S_current=0.0)
    _, comp = rs.score_memory(mem, q, e, NOW)
    assert math.isclose(comp["temporal"], math.exp(-0.1 * 10), rel_tol=1e-9)
