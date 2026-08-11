"""SC-1 extraction result (architecture doc §3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GoalExtractionResult:
    extraction_timestamp: Optional[datetime] = None
    message_id: str = ""
    goal_detected: bool = False
    is_update: bool = False
    goal_id_if_update: Optional[str] = None
    update_type: Optional[str] = None
    update_description: Optional[str] = None
    new_goal_data: Optional[dict] = None
    confidence: float = 0.0
    signal_strength: str = ""
    was_duplicate: bool = False
    matched_goal_id: Optional[str] = None
    processing_time_ms: int = 0
