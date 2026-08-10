"""SC-2 Background Emotional State Tracker types (architecture doc §4)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BESLabel(str, Enum):
    """Derived background-state label (architecture doc §4.3)."""

    STABLE_POSITIVE = "stable_positive"
    STABLE_NEUTRAL = "stable_neutral"
    MILD_NEGATIVE_DRIFT = "mild_negative_drift"
    SIGNIFICANT_NEGATIVE_DRIFT = "significant_negative_drift"
    IMPROVING = "improving"
    DETERIORATING = "deteriorating"
    VOLATILE = "volatile"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class BackgroundEmotionalState:
    """The user's emotional drift across time (architecture doc §4.3)."""

    valence_14day_mean: float = 0.0
    valence_trend: float = 0.0
    arousal_14day_mean: float = 0.0
    stressor_load: float = 0.0
    bes_label: str = BESLabel.INSUFFICIENT_DATA.value
    regulation_adjustment_applied: bool = False
    regulation_style: Optional[str] = None
    confidence: float = 0.0
    data_points_used: int = 0
    trend_note: Optional[str] = None
