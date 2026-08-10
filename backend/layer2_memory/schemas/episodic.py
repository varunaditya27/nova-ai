"""SC-2 Episodic Memory types (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from .emotion import EmotionVector


@dataclass
class RecallEvent:
    recalled_at: datetime
    trigger_query: str = ""
    score_at_recall: float = 0.0
    context_mode: str = ""
    was_used_in_response: bool = False


@dataclass
class EpisodicMemory:
    # Identity
    memory_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    session_id: Optional[UUID] = None

    # Content
    summary: str = ""
    embedding: list[float] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    entity_refs: list[str] = field(default_factory=list)
    thread_id: Optional[UUID] = None

    # Temporal
    created_at: Optional[datetime] = None
    session_timestamp: Optional[datetime] = None
    fuzzy_label: str = ""

    # Emotional
    emotion_vector: EmotionVector = field(default_factory=EmotionVector)
    emotional_weight: float = 0.0

    # Memory strength
    importance_score: float = 0.0
    base_importance: float = 0.0
    novelty_score: float = 0.0
    S0: float = 0.0
    S_current: float = 0.0
    decay_rate: float = 0.0
    last_decay_computed_at: Optional[datetime] = None
    reinforcement_count: int = 0
    is_archived: bool = False
    is_deleted: bool = False                       # logical deletion flag (non-destructive)

    # Layer-12 SC-3 user correction state (§5.5)
    is_anchored: bool = False                      # max persistence, decay frozen
    is_user_confirmed: bool = False
    is_user_downgraded: bool = False
    auto_expiry_date: Optional[date] = None
    last_corrected_at: Optional[datetime] = None

    # Lineage
    source_turn_ids: list[UUID] = field(default_factory=list)
    consolidated_into: Optional[UUID] = None
    linked_episodes: list[UUID] = field(default_factory=list)
    superseded_by: Optional[UUID] = None

    # Audit
    recall_history: list[RecallEvent] = field(default_factory=list)
    creation_agent: str = ""
