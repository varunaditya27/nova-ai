"""SC-2 Selective Deletion schemas (architecture doc §4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class DeletionType(str, Enum):
    SINGLE_MEMORY = "single_memory"
    TOPIC_BASED = "topic_based"
    SEMANTIC_WIPE = "semantic_wipe"
    IDENTITY_MEMORY = "identity_memory"
    LONGITUDINAL_DATA = "longitudinal_data"
    FULL_WIPE = "full_wipe"


DELETION_UNDO_WINDOWS = {
    DeletionType.SINGLE_MEMORY.value: timedelta(hours=1),
    DeletionType.TOPIC_BASED.value: timedelta(hours=1),
    DeletionType.SEMANTIC_WIPE.value: timedelta(hours=1),
    DeletionType.IDENTITY_MEMORY.value: timedelta(hours=24),
    DeletionType.LONGITUDINAL_DATA.value: timedelta(hours=1),
    DeletionType.FULL_WIPE.value: timedelta(0),
}

DELETION_CONFIRMATION_REQUIREMENTS = {
    DeletionType.SINGLE_MEMORY.value: "standard",
    DeletionType.TOPIC_BASED.value: "review_then_confirm",
    DeletionType.SEMANTIC_WIPE.value: "standard",
    DeletionType.IDENTITY_MEMORY.value: "extra",
    DeletionType.LONGITUDINAL_DATA.value: "review_then_confirm",
    DeletionType.FULL_WIPE.value: "extra_plus_passphrase",
}


@dataclass
class DeletionScope:
    memory_id: Optional[str] = None
    topic_tags: Optional[list] = None
    person_name: Optional[str] = None
    date_range: Optional[tuple] = None
    semantic_fact_ids: Optional[list] = None
    identity_entry_ids: Optional[list] = None
    chapter_ids: Optional[list] = None
    full_wipe_confirmed: bool = False


@dataclass
class CascadeImpactReport:
    memories_deleted: int = 0
    semantic_facts_affected: list = field(default_factory=list)   # (id, text, impact_type)
    personality_vector_will_change: bool = False
    personality_params_affected: list = field(default_factory=list)
    longitudinal_references_to_update: list = field(default_factory=list)
    summary_human_readable: str = ""


@dataclass
class DeletionRequest:
    user_id: str
    deletion_type: str
    scope: DeletionScope
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    requested_at: Optional[datetime] = None
    confirmation_required: str = "standard"
    undo_window_expiry: Optional[datetime] = None
    status: str = "pending"
    affected_memory_ids: list = field(default_factory=list)
    cascade_impacts: Optional[CascadeImpactReport] = None
    dry_run_completed: bool = False
    deletion_certificate: Optional[str] = None
    executed_at: Optional[datetime] = None


@dataclass
class DeletionCertificate:
    request_id: str
    deleted_count: int
    deleted_ids: list = field(default_factory=list)
    executed_at: Optional[datetime] = None
    payload_hash: str = ""
    signature: str = ""
    token: str = ""
