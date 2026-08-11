"""Emotion type shared with Layer 3 (docs/layer-2-architecture.md §4.2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmotionVector:
    """Valence/arousal emotional state (§4.2). Defined here as Layer 3 is not yet built."""

    valence: float = 0.0       # –1 (negative) … +1 (positive)
    arousal: float = 0.0       # 0 (calm) … 1 (activated)
    dominant_label: str = "neutral"
