"""SC-1 — Social Graph Manager (architecture doc §3).

Maintains a structured, persistent model of every named person in the user's social
world — built *exclusively* from what the user has stated, never inferred (§13
principle 2). The graph is the substrate every other Layer 5 sub-component reasons over.

Deterministic; the only embedding-dependent step (semantic entity resolution) accepts
an injected ``similarity_fn`` with a token-overlap default so the layer runs offline.

The graph itself is persisted/updated by the Layer 2 State Updater after each session
(§3.3); this module provides the pure functions that updater (and the orchestrator) use:
entity resolution, node creation, rolling valence update, and confidence decay.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer5_relationship.schemas import RelationshipType, SocialNode

# Keyword → relationship type for context-based inference (architecture doc §3.4).
_RELATIONSHIP_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("sister", "brother", "mom", "mum", "mother", "dad", "father", "parent", "sibling"),
     RelationshipType.FAMILY_IMMEDIATE.value),
    (("cousin", "aunt", "uncle", "grandma", "grandpa", "grandmother", "grandfather", "niece",
      "nephew"), RelationshipType.FAMILY_EXTENDED.value),
    (("partner", "boyfriend", "girlfriend", "husband", "wife", "spouse", "fiance", "fiancee"),
     RelationshipType.ROMANTIC_PARTNER.value),
    (("best friend", "close friend"), RelationshipType.CLOSE_FRIEND.value),
    (("manager", "boss", "supervisor"), RelationshipType.MANAGER.value),
    (("mentor",), RelationshipType.MENTOR.value),
    (("colleague", "coworker", "co-worker", "teammate"), RelationshipType.COLLEAGUE.value),
    (("professor", "doctor", "landlord", "teacher"), RelationshipType.AUTHORITY_FIGURE.value),
    (("classmate", "lab partner", "labmate"), RelationshipType.PEER_ACADEMIC.value),
    (("ex-boyfriend", "ex-girlfriend", "ex-husband", "ex-wife", "my ex"), RelationshipType.EX.value),
    (("friend",), RelationshipType.FRIEND.value),
]

# Entity-resolution thresholds (architecture doc §3.4).
_ALIAS_MATCH_CONFIDENCE = 0.95
_RELATIONSHIP_MATCH_CONFIDENCE = 0.70
_SEMANTIC_MATCH_FLOOR = 0.82
_RESOLUTION_FLOOR = 0.65
_TENTATIVE_LOW = 0.65
_TENTATIVE_HIGH = 0.80

# Confidence decay (architecture doc §3.3 Rule 3).
_DECAY_GRACE_DAYS = 90
_DECAY_PERIOD_DAYS = 30
_DECAY_STEP = 0.05


def infer_relationship_from_context(mention: str, context: str) -> Optional[str]:
    """Best-effort relationship type from keywords in the mention/context (§3.4)."""
    haystack = f"{mention} {context}".lower()
    for keywords, rel_type in _RELATIONSHIP_KEYWORDS:
        if any(kw in haystack for kw in keywords):
            return rel_type
    return None


def is_tentative_match(confidence: float) -> bool:
    """A match in [0.65, 0.80) is tentative — confirmed over later sessions (§3.4)."""
    return _TENTATIVE_LOW <= confidence < _TENTATIVE_HIGH


def resolve_entity(
    mention: str,
    context: str,
    existing_nodes: list[SocialNode],
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> tuple[Optional[str], float]:
    """Resolve a mention to an existing node (architecture doc §3.4).

    Returns ``(person_id, confidence)`` for a match, or ``(None, 0.0)`` for a new entity.
    Tries, in order: alias/name match (0.95), relationship-type-from-context match (0.70),
    and an injected semantic similarity (when > 0.82). Matches below 0.65 are treated as
    new entities.
    """
    mention_l = mention.lower().strip()
    candidates: list[tuple[str, float]] = []

    for node in existing_nodes:
        aliases = [a.lower() for a in node.name_aliases] + [node.display_name.lower()]
        if mention_l in aliases:
            candidates.append((node.person_id, _ALIAS_MATCH_CONFIDENCE))
            continue

        inferred = infer_relationship_from_context(mention, context)
        if inferred and inferred == node.relationship_type:
            candidates.append((node.person_id, _RELATIONSHIP_MATCH_CONFIDENCE))
            continue

        if similarity_fn is not None:
            sim = similarity_fn(
                f"{mention} {context}",
                f"{node.display_name} {node.relationship_subtype or ''}",
            )
            if sim > _SEMANTIC_MATCH_FLOOR:
                candidates.append((node.person_id, sim))

    if not candidates:
        return None, 0.0

    best = max(candidates, key=lambda x: x[1])
    if best[1] < _RESOLUTION_FLOOR:
        return None, 0.0
    return best


def create_node(
    display_name: str,
    relationship_type: str = RelationshipType.UNKNOWN.value,
    now: Optional[datetime] = None,
    **kwargs,
) -> SocialNode:
    """Create a new social node from a user mention (architecture doc §3.3 Rule 1)."""
    now = now or datetime.utcnow()
    return SocialNode(
        display_name=display_name,
        name_aliases=[display_name],
        relationship_type=relationship_type,
        first_mentioned=now,
        last_mentioned=now,
        mention_count=1,
        data_source="user_stated",
        **kwargs,
    )


def update_node_valence(node: SocialNode, new_valence: float, weight: float = 0.3) -> None:
    """Rolling weighted-average valence update, recent weighted more (§3.3 Rule 2)."""
    old = node.relationship_valence
    updated = (1.0 - weight) * old + weight * new_valence
    node.relationship_valence = max(-1.0, min(1.0, updated))
    node.valence_trend = node.relationship_valence - old
    node.valence_confidence = min(1.0, node.valence_confidence + 0.1)


def decay_confidence(node: SocialNode, now: Optional[datetime] = None) -> None:
    """Reduce confidence for nodes gone quiet 90+ days (architecture doc §3.3 Rule 3).

    0.05 reduction at 90 days, plus 0.05 per additional 30-day period. Marks staleness;
    never deletes. No-op when the node has been mentioned recently.
    """
    if node.last_mentioned is None:
        return
    now = now or datetime.utcnow()
    days = (now - node.last_mentioned).days
    if days < _DECAY_GRACE_DAYS:
        return
    extra_periods = (days - _DECAY_GRACE_DAYS) // _DECAY_PERIOD_DAYS
    reduction = _DECAY_STEP * (1 + extra_periods)
    node.confidence = max(0.0, node.confidence - reduction)
