"""SC-4 DriftDetectionResult (architecture doc §6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .enums import RecommendedAction, RiskLevel


@dataclass
class DriftDetectionResult:
    """Per-turn identity-consistency guard result (architecture doc §6.2)."""

    drift_detected: bool = False
    drift_type: Optional[str] = None
    affected_anchor: Optional[str] = None
    risk_level: str = RiskLevel.LOW.value
    recommended_action: str = RecommendedAction.PROCEED.value
    drift_note: Optional[str] = None
    # Plain-language directive injected into the Semantic Planner when drift fires.
    planner_directive: Optional[str] = None
