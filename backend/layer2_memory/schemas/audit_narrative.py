"""SC-8 Audit Trail + Narrative Chain types (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .enums import AuditEventType, ChainStatus, NarrativeLinkType


@dataclass
class AuditEvent:
    event_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    timestamp: Optional[datetime] = None
    event_type: AuditEventType = AuditEventType.MEMORY_CREATED
    memory_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    reason: str = ""
    score_at_event: Optional[float] = None
    prior_value: Optional[str] = None
    new_value: Optional[str] = None
    triggered_by: str = ""
    content_hash: str = ""
    prev_event_hash: str = ""


@dataclass
class ChainedEpisode:
    episode_id: UUID
    position_in_chain: int = 0
    link_type: NarrativeLinkType = NarrativeLinkType.CONTINUATION
    linked_at: Optional[datetime] = None


@dataclass
class NarrativeChain:
    chain_id: UUID = field(default_factory=uuid4)
    theme: str = ""
    episodes: list[ChainedEpisode] = field(default_factory=list)
    status: ChainStatus = ChainStatus.ACTIVE
    first_episode_at: Optional[datetime] = None
    last_episode_at: Optional[datetime] = None
    arc_summary: Optional[str] = None
