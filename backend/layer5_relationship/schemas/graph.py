"""SC-1 Social Graph dataclasses (architecture doc §3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .enums import InteractionFrequency, RelationshipType


@dataclass
class SocialNode:
    """One person in the user's social world — built only from what the user said (§3.2)."""

    person_id: str = field(default_factory=lambda: str(uuid4()))
    display_name: str = ""
    name_aliases: list[str] = field(default_factory=list)
    relationship_type: str = RelationshipType.UNKNOWN.value
    relationship_subtype: Optional[str] = None

    # Relationship valence
    relationship_valence: float = 0.0       # –1.0 … +1.0
    valence_confidence: float = 0.0
    valence_trend: float = 0.0              # slope; + improving, − worsening

    interaction_frequency: str = InteractionFrequency.UNKNOWN.value
    narrative_stability: float = 0.0

    # Conflict history
    active_conflict: bool = False
    conflict_count: int = 0
    conflict_topics: list[str] = field(default_factory=list)

    # Support role
    is_support_source: bool = False
    support_quality: Optional[float] = None

    first_mentioned: Optional[datetime] = None
    last_mentioned: Optional[datetime] = None
    mention_count: int = 0

    data_source: str = "user_stated"        # never inferred (§13 principle 2)
    confidence: float = 0.0


@dataclass
class SocialEdge:
    """A relationship edge; one endpoint is always the user (architecture doc §3.2)."""

    person_id_a: str = ""
    person_id_b: str = ""
    relationship_type: str = RelationshipType.UNKNOWN.value
    tie_strength: float = 0.0
    tie_strength_trend: float = 0.0
    last_interaction_reported: Optional[datetime] = None
    shared_contexts: list[str] = field(default_factory=list)
    co_mentions: list[str] = field(default_factory=list)


@dataclass
class SocialGraph:
    user_id: str = ""
    nodes: dict = field(default_factory=dict)   # person_id -> SocialNode
    edges: dict = field(default_factory=dict)   # (a, b) -> SocialEdge
    last_updated: Optional[datetime] = None
    version: int = 0
