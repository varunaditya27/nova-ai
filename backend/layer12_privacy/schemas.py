"""Schemas for Layer 12 — Privacy & Data Infrastructure (architecture doc §3-§7).

Pure-stdlib dataclasses + str-enums. Layer 12 is the trust architecture: On-Device Memory (SC-1),
Selective Deletion (SC-2), Memory Audit (SC-3), and Cross-Platform Sync (SC-4), coordinated by the
Privacy Agent. The authoritative deletion taxonomy is the six-type model (the scaffold's older
forget_* names are retired). Stores are duck-typed so the layer stays decoupled from concrete DBs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Optional


# ── SC-1 integrity (§3.4) ─────────────────────────────────────────────────────
@dataclass
class IntegrityCheckResult:
    status: str = "INTACT"               # INTACT | TAMPER_DETECTED | CHECK_FAILED
    checked_at: Optional[datetime] = None
    current_root: str = ""
    expected_root: str = ""
    mismatch_details: Optional[str] = None


# ── SC-2 selective deletion (§4) ──────────────────────────────────────────────
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
    semantic_category: Optional[str] = None
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
    chapters_affected: list = field(default_factory=list)
    chapter_merge_required: bool = False
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


# ── SC-3 memory audit (§5) ────────────────────────────────────────────────────
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


# ── SC-4 sync (§6) ────────────────────────────────────────────────────────────
@dataclass
class SyncOperation:
    operation_type: str
    record_id: str
    store_name: str
    serialized_record: Any = None
    timestamp: Optional[datetime] = None


@dataclass
class SyncDelta:
    user_id: str
    source_device_id: str
    delta_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: Optional[datetime] = None
    sequence_number: int = 0
    previous_delta_id: Optional[str] = None
    encrypted_payload: str = ""
    payload_size_bytes: int = 0


@dataclass
class ResolvedOperation:
    action: str                           # insert | overwrite | keep_local | hold_pending_user_resolution
    record: Any = None
    notify: Optional[str] = None


@dataclass
class SyncConfiguration:
    user_id: str
    sync_enabled: bool = True
    sync_episodic_memory: bool = True
    sync_semantic_memory: bool = True
    sync_identity_memory: bool = True
    sync_personality_vector: bool = True
    sync_longitudinal_data: bool = True
    sync_goal_state: bool = True
    sync_safety_record: bool = False      # most sensitive; off by default


# ── Privacy Agent — consent (§7) ──────────────────────────────────────────────
CONSENT_TYPES = [
    "cloud_backup_sync", "usage_telemetry", "weekly_summary_delivery",
    "proactive_checkins", "crisis_session_logging", "memory_for_personalization",
]
_NON_REVOCABLE_CONSENTS = {"crisis_session_logging"}


@dataclass
class ConsentRecord:
    user_id: str
    consent_type: str
    granted: bool
    consent_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    user_initiated: bool = True
    version: str = "1.0"
