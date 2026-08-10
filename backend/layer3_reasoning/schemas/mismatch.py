"""SC-4 Stated-vs-Felt Mismatch Detector types (architecture doc §6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MismatchType(str, Enum):
    """How the stated emotion diverges from the felt estimate (architecture doc §6.2)."""

    MINIMIZING = "minimizing"
    MASKING = "masking"
    OVERCLAIMING = "overclaiming"
    LINGUISTIC_HEDGING = "linguistic_hedging"


class MismatchPosture(str, Enum):
    """How Nova should hold a detected mismatch (architecture doc §6.3)."""

    GENTLE_ACKNOWLEDGMENT = "gentle_acknowledgment"  # Posture 1 (default)
    DIRECT_NOTICING = "direct_noticing"              # Posture 2 (needs depth + confidence)
    HOLD_AND_WATCH = "hold_and_watch"                # Posture 3 (uncertain / new relationship)


@dataclass
class MismatchResult:
    """Gap between stated content and felt state (architecture doc §6.2)."""

    mismatch_detected: bool = False
    mismatch_type: Optional[str] = None
    stated_valence: float = 0.0
    felt_valence_estimate: float = 0.0
    mismatch_magnitude: float = 0.0
    mismatch_confidence: float = 0.0
    hedging_phrases_detected: list[str] = field(default_factory=list)
    deflection_phrases_detected: list[str] = field(default_factory=list)
    mismatch_response_posture: Optional[str] = None
