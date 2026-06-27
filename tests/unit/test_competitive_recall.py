"""Tests for SC-6 competitive recall: softmax, effective score, cap-3 (architecture doc §8.4, §8.6)."""

import math

from backend.layer2_memory import competitive_recall as cr
from backend.layer2_memory.schemas import (
    ConversationMode,
    EpisodicMemory,
    ScoredMemory,
)


def test_softmax_sums_to_one():
    probs = cr.softmax([1.0, 2.0, 3.0], tau=0.7)
    assert math.isclose(sum(probs), 1.0, rel_tol=1e-9)


def test_softmax_lower_temperature_sharpens():
    sharp = cr.softmax([1.0, 2.0], tau=0.3)
    soft = cr.softmax([1.0, 2.0], tau=1.2)
    # lower τ concentrates more probability on the top scorer
    assert sharp[1] > soft[1]


def test_softmax_empty_returns_empty():
    assert cr.softmax([], tau=0.7) == []


def test_effective_score_is_product():
    # EffectiveScore = RecallScore × S(t) × G
    assert cr.effective_score(recall_score=0.8, s_current=0.5, gate_value=0.5) == 0.2


def test_temperature_for_mode():
    assert cr.temperature_for_mode(ConversationMode.TECHNICAL_DISCUSSION) == 0.3
    assert cr.temperature_for_mode(ConversationMode.CASUAL) == 0.5
    assert cr.temperature_for_mode(ConversationMode.EMOTIONAL_SUPPORT) == 0.7


def _scored(eff):
    return ScoredMemory(memory=EpisodicMemory(), effective_score=eff)


def test_select_recall_caps_at_three_sorted_descending():
    scored = [_scored(e) for e in (0.2, 0.9, 0.5, 0.7, 0.1)]
    selected = cr.select_recall(scored, cap=3)
    assert [s.effective_score for s in selected] == [0.9, 0.7, 0.5]


def test_select_recall_drops_zero_gated_memories():
    # A memory fully suppressed by the gate (effective_score 0) is not surfaced.
    scored = [_scored(0.0), _scored(0.4)]
    selected = cr.select_recall(scored, cap=3)
    assert len(selected) == 1
    assert selected[0].effective_score == 0.4


def test_select_recall_empty():
    assert cr.select_recall([], cap=3) == []
