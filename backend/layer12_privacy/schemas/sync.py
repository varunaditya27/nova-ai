"""SC-4 Cross-Platform Sync schemas (architecture doc §6)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


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
