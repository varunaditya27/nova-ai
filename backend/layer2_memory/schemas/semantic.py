"""SC-3 Semantic Memory types (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .enums import SemanticMemoryType


@dataclass
class SemanticMemory:
    memory_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    memory_type: SemanticMemoryType = SemanticMemoryType.FACTUAL_STABLE

    statement: str = ""
    embedding: list[float] = field(default_factory=list)
    confidence: float = 0.5
    supporting_episode_ids: list[UUID] = field(default_factory=list)
    evidence_count: int = 0

    created_at: Optional[datetime] = None
    last_confirmed_at: Optional[datetime] = None
    last_contradicted_at: Optional[datetime] = None
    contradiction_count: int = 0

    decay_rate: float = 0.005
    S_current: float = 1.0
    is_deprecated: bool = False

    retrieval_tags: list[str] = field(default_factory=list)
    relevance_contexts: list[str] = field(default_factory=list)
