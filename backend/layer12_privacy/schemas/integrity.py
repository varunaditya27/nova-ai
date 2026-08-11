"""SC-1 integrity check contract (architecture doc §3.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class IntegrityCheckResult:
    status: str = "INTACT"               # INTACT | TAMPER_DETECTED | CHECK_FAILED
    checked_at: Optional[datetime] = None
    current_root: str = ""
    expected_root: str = ""
    mismatch_details: Optional[str] = None
