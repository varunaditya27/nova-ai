"""SC-3 progress classification + state change (architecture doc §5)."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import ProgressSignalType


@dataclass
class ProgressSignalClassification:
    signal_type: str = ProgressSignalType.PROGRESS_POSITIVE.value
    confidence: float = 0.0
    evidence: str = ""


@dataclass
class GoalStateChange:
    goal_id: str = ""
    new_status: str = ""
    reason: str = ""
