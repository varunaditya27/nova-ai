"""SC-3 Memory Audit + Correction schemas (architecture doc §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


@dataclass
class AuditableMemory:
    memory_id: str
    date_formed: Optional[date] = None
    human_readable_summary: str = ""
    importance_label: str = "Low"
    topic_tags: list = field(default_factory=list)
    emotion_at_formation: str = "neutral"
    reinforcement_count: int = 0
    derived_semantic_facts: list = field(default_factory=list)


@dataclass
class AuditableFact:
    fact_id: str
    fact_text: str = ""
    category: str = ""
    confidence: float = 0.0
    source_episode_ids: list = field(default_factory=list)
    is_user_confirmed: bool = False
    expiry_date: Optional[date] = None


@dataclass
class MemoryAuditView:
    user_id: str
    generated_at: Optional[datetime] = None
    total_memory_count: int = 0
    episodic: list = field(default_factory=list)        # AuditableMemory
    semantic: list = field(default_factory=list)        # AuditableFact
    identity: list = field(default_factory=list)
    crisis_session_count: int = 0
    active_goal_count: int = 0


@dataclass
class AuditQueryResult:
    query: str
    records: list = field(default_factory=list)
    total_count: int = 0
    intent_type: str = "topic_query"


@dataclass
class ProvenanceRecord:
    memory_id: str
    memory_type: str = "episodic"
    primary_session_id: Optional[str] = None
    first_formed: Optional[date] = None
    last_reinforced: Optional[date] = None
    total_reinforcement_count: int = 0
    contributed_to_semantic_facts: list = field(default_factory=list)


class MemoryCorrectionType(str, Enum):
    EDIT = "edit"
    DOWNGRADE = "downgrade"
    DECONTEXTUALIZE = "decontextualize"
    ANCHOR = "anchor"
    EXPIRE = "expire"
    CONFIRM = "confirm"


@dataclass
class MemoryCorrectionRequest:
    memory_id: str
    correction_type: str
    new_content: Optional[str] = None
    new_importance: Optional[str] = None      # "Low" | "Medium"
    tags_to_remove: Optional[list] = None
    expiry_date: Optional[date] = None


@dataclass
class CorrectionResult:
    success: bool
    memory_id: str
    correction_type: str = ""
    detail: str = ""
