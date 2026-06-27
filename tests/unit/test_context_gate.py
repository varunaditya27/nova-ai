"""Tests for SC-6 context gate (architecture doc §8.5).

Gate table reconciled to Layer 3's canonical conversation modes (casual, crisis, +celebration).
"""

import pytest

from backend.layer2_memory import context_gate as cg
from backend.layer2_memory.schemas import (
    ConversationMode,
    EpisodicMemory,
    IdentityMemory,
    SemanticMemory,
)


@pytest.mark.parametrize(
    "mode,kind,expected",
    [
        (ConversationMode.CASUAL, "episodic_emotional", 0.10),
        (ConversationMode.CASUAL, "semantic", 0.50),
        (ConversationMode.EMOTIONAL_SUPPORT, "episodic_emotional", 1.00),
        (ConversationMode.CRISIS, "episodic_emotional", 1.00),
        (ConversationMode.CRISIS, "identity", 0.10),
        (ConversationMode.TECHNICAL_DISCUSSION, "episodic_factual", 0.70),
        (ConversationMode.GOAL_PLANNING, "semantic", 0.90),
        (ConversationMode.SOCIAL_COACHING, "episodic_emotional", 0.60),
        (ConversationMode.LIFE_REVIEW, "episodic_factual", 0.90),
    ],
)
def test_gate_value_table(mode, kind, expected):
    assert cg.gate_value(mode, kind) == expected


def test_celebration_mode_is_defined():
    # Reconciliation: celebration was absent from the doc table; added emotion-forward values.
    assert cg.gate_value(ConversationMode.CELEBRATION, "episodic_emotional") > 0.5


def test_all_canonical_modes_have_gate_rows():
    for mode in ConversationMode:
        for kind in ("episodic_emotional", "episodic_factual", "semantic", "identity"):
            v = cg.gate_value(mode, kind)
            assert 0.0 <= v <= 1.0


def test_episodic_kind_classifies_by_emotional_weight():
    emotional = EpisodicMemory(emotional_weight=0.8)
    factual = EpisodicMemory(emotional_weight=0.1)
    assert cg.memory_gate_kind(emotional) == "episodic_emotional"
    assert cg.memory_gate_kind(factual) == "episodic_factual"


def test_memory_gate_kind_for_semantic_and_identity():
    assert cg.memory_gate_kind(SemanticMemory()) == "semantic"
    assert cg.memory_gate_kind(IdentityMemory()) == "identity"
