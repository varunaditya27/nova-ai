"""Tests for SC-2 Background Emotional State Tracker (architecture doc §4)."""

import math
from datetime import datetime, timedelta

from backend.layer3_reasoning import background_state as bes
from backend.layer3_reasoning.schemas import BESLabel, BackgroundEmotionalState
from backend.layer2_memory.schemas import (
    EmotionVector,
    EpisodicMemory,
    PsychologicalModel,
    Stressor,
)

NOW = datetime(2026, 6, 26)


def _ep(valence, arousal, days_ago):
    return EpisodicMemory(
        emotion_vector=EmotionVector(valence=valence, arousal=arousal),
        created_at=NOW - timedelta(days=days_ago),
    )


# ── Linear slope helper (§4.2) ───────────────────────────────────────────────
def test_linear_slope_positive_for_rising_series():
    assert bes.compute_linear_slope([0, 1, 2, 3], [0.0, 0.1, 0.2, 0.3]) > 0


def test_linear_slope_negative_for_falling_series():
    assert bes.compute_linear_slope([0, 1, 2, 3], [0.3, 0.2, 0.1, 0.0]) < 0


def test_linear_slope_zero_for_single_point():
    assert bes.compute_linear_slope([0], [0.5]) == 0.0


# ── Episodic valence trend (§4.2) ────────────────────────────────────────────
def test_valence_trend_insufficient_data_returns_neutral():
    mean, slope = bes.compute_episodic_valence_trend([_ep(0.5, 0.3, 1)], now=NOW)
    assert mean == 0.0 and slope == 0.0


def test_valence_trend_detects_worsening():
    eps = [_ep(0.4, 0.3, 12), _ep(0.0, 0.4, 8), _ep(-0.4, 0.5, 4), _ep(-0.7, 0.6, 1)]
    mean, slope = bes.compute_episodic_valence_trend(eps, now=NOW)
    assert slope < 0           # worsening over time
    assert mean < 0.2          # weighted toward the recent negative end


def test_valence_trend_ignores_memories_outside_window():
    eps = [_ep(-0.9, 0.5, 40), _ep(0.5, 0.3, 2), _ep(0.5, 0.3, 1)]
    mean, _ = bes.compute_episodic_valence_trend(eps, window_days=14, now=NOW)
    assert mean > 0.0          # the 40-day-old negative memory is excluded


# ── Stressor load (§4.2) ─────────────────────────────────────────────────────
def test_stressor_load_zero_when_none():
    assert bes.compute_stressor_load([]) == 0.0


def test_stressor_load_high_for_intense_recent_stressors():
    stressors = [
        Stressor(intensity=0.9, duration_days=10),
        Stressor(intensity=0.8, duration_days=15),
    ]
    assert bes.compute_stressor_load(stressors) > 0.5


def test_stressor_load_capped_at_one():
    stressors = [Stressor(intensity=1.0, duration_days=1) for _ in range(10)]
    assert bes.compute_stressor_load(stressors) == 1.0


# ── BES label derivation (§4.3) ──────────────────────────────────────────────
def test_bes_insufficient_data_with_few_memories():
    state = bes.compute_background_state([], now=NOW)
    assert state.bes_label == BESLabel.INSUFFICIENT_DATA.value
    assert state.confidence < 0.3


def test_bes_stable_positive():
    eps = [_ep(0.6, 0.3, d) for d in (10, 7, 4, 2, 1)]
    state = bes.compute_background_state(eps, now=NOW)
    assert state.bes_label == BESLabel.STABLE_POSITIVE.value


def test_bes_significant_negative_drift():
    eps = [_ep(-0.7, 0.5, d) for d in (10, 7, 4, 2, 1)]
    state = bes.compute_background_state(eps, now=NOW)
    assert state.bes_label == BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value


def test_bes_improving_when_negative_mean_but_rising_trend():
    eps = [_ep(-0.8, 0.5, 12), _ep(-0.5, 0.4, 8), _ep(-0.2, 0.3, 4), _ep(0.1, 0.3, 1)]
    state = bes.compute_background_state(eps, now=NOW)
    assert state.bes_label == BESLabel.IMPROVING.value
    assert state.trend_note is not None


def test_bes_high_stressor_load_forces_significant_drift():
    eps = [_ep(0.1, 0.3, d) for d in (10, 7, 4, 2, 1)]
    stressors = [Stressor(intensity=1.0, duration_days=5) for _ in range(5)]
    state = bes.compute_background_state(eps, active_stressors=stressors, now=NOW)
    assert state.bes_label == BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value


# ── Regulation-style adjustment (§4.2) ───────────────────────────────────────
def test_minimizer_regulation_shifts_bes_more_negative():
    eps = [_ep(-0.3, 0.4, d) for d in (10, 7, 4, 2, 1)]
    psych = PsychologicalModel(emotional_regulation_style="minimizer")
    state = bes.compute_background_state(eps, psychological_model=psych, now=NOW)
    assert state.regulation_adjustment_applied is True
    assert state.regulation_style == "minimizer"
    assert state.valence_14day_mean < -0.3   # shifted further negative than expressed


def test_confidence_grows_with_data_points():
    few = bes.compute_background_state([_ep(0.2, 0.3, d) for d in (5, 3, 1)], now=NOW)
    many = bes.compute_background_state([_ep(0.2, 0.3, d) for d in range(1, 13)], now=NOW)
    assert many.confidence > few.confidence
