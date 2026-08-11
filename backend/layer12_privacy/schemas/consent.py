"""Privacy Agent — consent schemas (architecture doc §7)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

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
