"""SC-2 — Background Emotional State Tracker (architecture doc §4).

The BES reads the *person*, not the *message*. It is derived entirely from Layer 2 data
(no current-message input): a rolling 14-day exponentially-weighted valence trend, an
active-stressor load, and psychological-model adjustments (e.g. a ``minimizer`` whose
stated affect systematically understates the felt state). It contextualises — never
overrides — the Primary Emotion (§4.4).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from backend.layer3_reasoning.schemas import BESLabel, BackgroundEmotionalState

WINDOW_DAYS = 14
MIN_DATA_POINTS = 3
STRONG_SLOPE = 0.02            # valence units per day that counts as a real trend
HIGH_STRESSOR_LOAD = 0.7
VOLATILE_STDEV = 0.5
MINIMIZER_SHIFT = 0.15         # how far a minimizer's BES is pulled below stated affect


def compute_linear_slope(xs: list[float], ys: list[float]) -> float:
    """Ordinary least-squares slope of ys over xs; 0 for <2 points (architecture doc §4.2)."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return num / denom


def _recent(memories, window_days, now):
    """Memories inside the window, sorted oldest→newest, with valid timestamps."""
    out = [m for m in memories
           if m.created_at is not None and (now - m.created_at).days <= window_days]
    out.sort(key=lambda m: m.created_at)
    return out


def compute_episodic_valence_trend(
    episodic_memories,
    window_days: int = WINDOW_DAYS,
    now: Optional[datetime] = None,
) -> tuple[float, float]:
    """Return (exp-weighted mean valence, valence trend slope) over the window (§4.2)."""
    now = now or datetime.utcnow()
    recent = _recent(episodic_memories, window_days, now)
    if len(recent) < 2:
        return 0.0, 0.0

    # Exponentially weight recent memories more heavily.
    weights = [math.exp(-0.1 * i) for i in range(len(recent) - 1, -1, -1)]
    weighted_valence = sum(
        m.emotion_vector.valence * w for m, w in zip(recent, weights)
    ) / sum(weights)

    timestamps = [(m.created_at - recent[0].created_at).days for m in recent]
    valences = [m.emotion_vector.valence for m in recent]
    slope = compute_linear_slope(timestamps, valences)
    return weighted_valence, slope


def compute_stressor_load(active_stressors) -> float:
    """0–1 background-pressure score; recent stressors weigh more (architecture doc §4.2)."""
    if not active_stressors:
        return 0.0
    total = sum(
        s.intensity * (1 / max(1.0, s.duration_days / 30)) for s in active_stressors
    )
    return min(total / 3.0, 1.0)


def _derive_label(mean: float, slope: float, stressor_load: float,
                  stdev: float, n: int) -> str:
    """Map the numeric state onto a BES label (architecture doc §4.3)."""
    if n < MIN_DATA_POINTS:
        return BESLabel.INSUFFICIENT_DATA.value

    # High background pressure dominates unless affect is clearly positive.
    if stressor_load >= HIGH_STRESSOR_LOAD and mean < 0.3:
        return BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value

    # Trend-based labels take priority over static range labels.
    if mean < -0.05 and slope >= STRONG_SLOPE:
        return BESLabel.IMPROVING.value
    if -0.2 <= mean <= 0.3 and slope <= -STRONG_SLOPE:
        return BESLabel.DETERIORATING.value
    if stdev > VOLATILE_STDEV and abs(slope) < STRONG_SLOPE:
        return BESLabel.VOLATILE.value

    # Static ranges.
    if mean > 0.3:
        return BESLabel.STABLE_POSITIVE.value
    if mean >= -0.2:
        return BESLabel.STABLE_NEUTRAL.value
    if mean >= -0.5:
        return BESLabel.MILD_NEGATIVE_DRIFT.value
    return BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value


def compute_background_state(
    episodic_memories,
    active_stressors=None,
    psychological_model=None,
    window_days: int = WINDOW_DAYS,
    now: Optional[datetime] = None,
) -> BackgroundEmotionalState:
    """Synthesise the BES from Layer 2 data (architecture doc §4.2, §4.3)."""
    now = now or datetime.utcnow()
    active_stressors = active_stressors or []

    recent = _recent(episodic_memories, window_days, now)
    n = len(recent)
    mean_valence, slope = compute_episodic_valence_trend(episodic_memories, window_days, now)

    arousals = [m.emotion_vector.arousal for m in recent]
    arousal_mean = sum(arousals) / len(arousals) if arousals else 0.0

    valences = [m.emotion_vector.valence for m in recent]
    if len(valences) >= 2:
        v_mean = sum(valences) / len(valences)
        stdev = (sum((v - v_mean) ** 2 for v in valences) / len(valences)) ** 0.5
    else:
        stdev = 0.0

    stressor_load = compute_stressor_load(active_stressors)

    # Regulation-style adjustment: a minimizer understates, so pull the BES negative.
    regulation_applied = False
    regulation_style = None
    if psychological_model is not None and psychological_model.emotional_regulation_style:
        regulation_style = psychological_model.emotional_regulation_style
        if regulation_style == "minimizer":
            mean_valence = max(-1.0, mean_valence - MINIMIZER_SHIFT)
            regulation_applied = True

    label = _derive_label(mean_valence, slope, stressor_load, stdev, n)

    trend_note = None
    if label == BESLabel.IMPROVING.value:
        trend_note = "has been improving over the past week"
    elif label == BESLabel.DETERIORATING.value:
        trend_note = "has been trending downward recently"

    confidence = 0.1 if n == 0 else min(0.95, 0.1 + 0.07 * n)

    return BackgroundEmotionalState(
        valence_14day_mean=mean_valence,
        valence_trend=slope,
        arousal_14day_mean=arousal_mean,
        stressor_load=stressor_load,
        bes_label=label,
        regulation_adjustment_applied=regulation_applied,
        regulation_style=regulation_style,
        confidence=confidence,
        data_points_used=n,
        trend_note=trend_note,
    )
