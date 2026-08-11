"""SC-7 Forgetting & Consolidation Engine output types (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .episodic import EpisodicMemory


@dataclass
class EpisodicCluster:
    members: list[EpisodicMemory] = field(default_factory=list)

    @property
    def most_recent_episode(self) -> Optional[EpisodicMemory]:
        dated = [e for e in self.members if e.created_at is not None]
        if dated:
            return max(dated, key=lambda e: e.created_at)
        return self.members[0] if self.members else None


@dataclass
class FCERunReport:
    run_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    run_at: Optional[datetime] = None
    trigger_reason: str = ""
    episodes_evaluated: int = 0
    episodes_deleted: int = 0
    episodes_archived: int = 0
    clusters_detected: int = 0
    semantic_memories_created: int = 0
    episodes_consolidated: int = 0
    new_semantic_summaries: list[str] = field(default_factory=list)
    next_scheduled_run: Optional[datetime] = None
