"""Tests for SC-3 semantic memory: confidence + contradiction handling (architecture doc §5.3)."""

from datetime import datetime

from backend.layer2_memory import semantic_memory as sm
from backend.layer2_memory.schemas import EpisodicMemory, SemanticMemory

NOW = datetime(2026, 6, 26)


def test_initial_confidence_scales_with_cluster_size():
    assert sm.compute_initial_confidence(3) == 0.65   # 0.5 + 0.05*3
    assert sm.compute_initial_confidence(5) == 0.75


def test_initial_confidence_capped():
    assert sm.compute_initial_confidence(20) == 0.95   # cap


def test_required_contradictions_formula():
    # ceil(2 + confidence*6). NOTE: doc inline comment "0.3 → 3" is off by one; the
    # formula yields 4. The high-confidence example (0.9 → 8) matches the formula.
    assert sm.required_contradictions(0.3) == 4
    assert sm.required_contradictions(0.9) == 8


def test_single_contradiction_reduces_confidence():
    semantic = SemanticMemory(statement="User loves early mornings", confidence=0.8)
    evidence = EpisodicMemory(importance_score=0.6, S_current=1.0)
    sm.handle_contradiction(semantic, evidence, now=NOW)
    assert semantic.contradiction_count == 1
    assert semantic.is_deprecated is False
    # confidence reduced by importance*S_current*0.15 = 0.6*1.0*0.15 = 0.09
    assert abs(semantic.confidence - (0.8 - 0.09)) < 1e-9
    assert semantic.last_contradicted_at == NOW


def test_accumulated_contradictions_deprecate():
    semantic = SemanticMemory(statement="User avoids conflict", confidence=0.3)  # needs 4
    evidence = EpisodicMemory(importance_score=0.5, S_current=1.0)
    for _ in range(4):
        sm.handle_contradiction(semantic, evidence, now=NOW)
    assert semantic.is_deprecated is True


def test_confidence_floor():
    semantic = SemanticMemory(confidence=0.2)
    strong = EpisodicMemory(importance_score=1.0, S_current=1.0)  # would drop 0.15
    sm.handle_contradiction(semantic, strong, now=NOW)
    assert semantic.confidence >= 0.1
