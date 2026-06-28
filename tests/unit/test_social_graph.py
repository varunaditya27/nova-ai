"""Tests for SC-1 Social Graph Manager (architecture doc §3)."""

from datetime import datetime, timedelta

from backend.layer5_relationship import social_graph as sg
from backend.layer5_relationship.schemas import (
    RelationshipType,
    SocialNode,
)

NOW = datetime(2026, 6, 28)


# ── Relationship inference from context (§3.4) ───────────────────────────────
def test_infer_relationship_from_keywords():
    assert sg.infer_relationship_from_context("my sister", "she called me") == \
        RelationshipType.FAMILY_IMMEDIATE.value
    assert sg.infer_relationship_from_context("my manager", "at work today") == \
        RelationshipType.MANAGER.value
    assert sg.infer_relationship_from_context("the weather", "it rained") is None


# ── Entity resolution (§3.4) ─────────────────────────────────────────────────
def test_resolve_entity_alias_match_is_high_confidence():
    node = SocialNode(display_name="Priya", name_aliases=["Priya", "my sister"],
                      relationship_type=RelationshipType.FAMILY_IMMEDIATE.value)
    pid, conf = sg.resolve_entity("priya", "she called", [node])
    assert pid == node.person_id
    assert conf >= 0.95


def test_resolve_entity_by_relationship_type():
    node = SocialNode(display_name="Priya", name_aliases=["Priya"],
                      relationship_type=RelationshipType.FAMILY_IMMEDIATE.value)
    pid, conf = sg.resolve_entity("my sister", "we talked", [node])
    assert pid == node.person_id
    assert 0.65 <= conf < 0.80


def test_resolve_entity_new_person_returns_none():
    node = SocialNode(display_name="Priya", name_aliases=["Priya"],
                      relationship_type=RelationshipType.FAMILY_IMMEDIATE.value)
    pid, conf = sg.resolve_entity("my coworker Dan", "at the office", [node])
    assert pid is None
    assert conf == 0.0


def test_resolve_entity_uses_injected_similarity_fn():
    node = SocialNode(display_name="my lab partner", relationship_subtype="lab partner",
                      relationship_type=RelationshipType.PEER_ACADEMIC.value)
    pid, conf = sg.resolve_entity("the person from my lab", "research project",
                                  [node], similarity_fn=lambda a, b: 0.9)
    assert pid == node.person_id
    assert conf >= 0.82


def test_resolve_entity_below_threshold_is_new():
    node = SocialNode(display_name="Priya", relationship_type=RelationshipType.FRIEND.value)
    pid, conf = sg.resolve_entity("someone", "vague", [node], similarity_fn=lambda a, b: 0.4)
    assert pid is None and conf == 0.0


# ── Tentative-match window (§3.4) ────────────────────────────────────────────
def test_is_tentative_match_window():
    assert sg.is_tentative_match(0.70) is True
    assert sg.is_tentative_match(0.85) is False
    assert sg.is_tentative_match(0.60) is False


# ── Node creation (§3.3 Rule 1) ──────────────────────────────────────────────
def test_create_node_defaults():
    node = sg.create_node("my manager", RelationshipType.MANAGER.value, now=NOW)
    assert node.display_name == "my manager"
    assert node.data_source == "user_stated"
    assert node.first_mentioned == NOW
    assert node.last_mentioned == NOW
    assert node.mention_count == 1
    assert "my manager" in node.name_aliases


# ── Valence rolling update (§3.3 Rule 2) ─────────────────────────────────────
def test_update_node_valence_rolling_average_and_trend():
    node = SocialNode(relationship_valence=0.0, valence_confidence=0.2)
    sg.update_node_valence(node, 1.0, weight=0.3)
    assert abs(node.relationship_valence - 0.3) < 1e-9   # (1-0.3)*0 + 0.3*1.0
    assert node.valence_trend > 0                          # improving
    assert node.valence_confidence > 0.2                   # confidence grows with evidence


def test_update_node_valence_negative_trend():
    node = SocialNode(relationship_valence=0.5)
    sg.update_node_valence(node, -0.5, weight=0.3)
    assert node.valence_trend < 0                          # worsening


# ── Confidence decay (§3.3 Rule 3) ───────────────────────────────────────────
def test_decay_confidence_after_long_silence():
    node = SocialNode(confidence=0.8, last_mentioned=NOW - timedelta(days=120))
    sg.decay_confidence(node, now=NOW)
    # 120 days = 90 + one extra 30-day period → 0.05 * 2 = 0.10 reduction
    assert abs(node.confidence - 0.70) < 1e-9


def test_decay_confidence_recent_mention_unchanged():
    node = SocialNode(confidence=0.8, last_mentioned=NOW - timedelta(days=10))
    sg.decay_confidence(node, now=NOW)
    assert node.confidence == 0.8
