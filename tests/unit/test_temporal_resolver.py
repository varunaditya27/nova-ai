"""Tests for Layer 1 SC-1 — Temporal Resolver (architecture doc §3).

Covers the §12.3 testing requirements: circadian band mapping across the full 24h range,
gap classification across all 7 buckets and boundaries, anomaly detection conditions, and
fuzzy-label correctness.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from backend.layer1_input import temporal_resolver as tr
from backend.layer1_input.schemas import (
    CircadianBand,
    GapCategory,
    UserTemporalProfile,
)


# ── Circadian band mapping (§3.2) ───────────────────────────────────────────
@pytest.mark.parametrize(
    "hour,expected",
    [
        (0, CircadianBand.LATE_NIGHT), (1, CircadianBand.LATE_NIGHT),
        (2, CircadianBand.LATE_NIGHT), (23, CircadianBand.LATE_NIGHT),
        (3, CircadianBand.EARLY_MORNING), (5, CircadianBand.EARLY_MORNING),
        (6, CircadianBand.MORNING), (11, CircadianBand.MORNING),
        (12, CircadianBand.AFTERNOON), (16, CircadianBand.AFTERNOON),
        (17, CircadianBand.EVENING), (20, CircadianBand.EVENING),
        (21, CircadianBand.NIGHT), (22, CircadianBand.NIGHT),
    ],
)
def test_map_circadian_band(hour, expected):
    assert tr.map_circadian_band(hour) == expected


def test_every_hour_maps_to_a_band():
    # §12.3: 100% of the 24-hour range must map to exactly one band.
    bands = {tr.map_circadian_band(h) for h in range(24)}
    assert bands == set(CircadianBand)


def test_circadian_mood_prior_defaults():
    expected = {
        CircadianBand.LATE_NIGHT: 0.75,
        CircadianBand.EARLY_MORNING: 0.80,
        CircadianBand.MORNING: 0.20,
        CircadianBand.AFTERNOON: 0.25,
        CircadianBand.EVENING: 0.40,
        CircadianBand.NIGHT: 0.55,
    }
    for band, prior in expected.items():
        assert tr.circadian_mood_prior(band) == prior


def test_circadian_mood_prior_personalized_after_20_sessions():
    profile = UserTemporalProfile(
        user_id=uuid4(),
        total_sessions=25,
        per_band_circadian_prior={"late_night": 0.40},
    )
    # Personalized prior overrides the population default once 20+ sessions exist.
    assert tr.circadian_mood_prior(CircadianBand.LATE_NIGHT, profile) == 0.40


def test_circadian_mood_prior_ignores_personalization_below_20_sessions():
    profile = UserTemporalProfile(
        user_id=uuid4(),
        total_sessions=10,
        per_band_circadian_prior={"late_night": 0.40},
    )
    assert tr.circadian_mood_prior(CircadianBand.LATE_NIGHT, profile) == 0.75


# ── Session gap classification (§3.3) ───────────────────────────────────────
@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, GapCategory.SAME_SESSION),
        (1799, GapCategory.SAME_SESSION),
        (1800, GapCategory.SHORT_BREAK),
        (14399, GapCategory.SHORT_BREAK),
        (14400, GapCategory.SAME_DAY),
        (86399, GapCategory.SAME_DAY),
        (86400, GapCategory.FEW_DAYS),
        (259199, GapCategory.FEW_DAYS),
        (259200, GapCategory.WEEK_OR_TWO),
        (1209599, GapCategory.WEEK_OR_TWO),
        (1209600, GapCategory.LONG_ABSENCE),
        (7775999, GapCategory.LONG_ABSENCE),
        (7776000, GapCategory.VERY_LONG_ABSENCE),
        (50_000_000, GapCategory.VERY_LONG_ABSENCE),
    ],
)
def test_classify_session_gap_boundaries(seconds, expected):
    assert tr.classify_session_gap(seconds) == expected


def test_gap_label_for_every_category():
    # Every category must yield a non-empty human-readable label (never a raw number).
    for category in GapCategory:
        label = tr.gap_label(category)
        assert isinstance(label, str) and label
        assert not any(ch.isdigit() for ch in label)


def test_is_new_session_aligns_with_gap_category():
    assert tr.is_new_session(0) is False
    assert tr.is_new_session(1799) is False
    assert tr.is_new_session(1800) is True
    assert tr.is_new_session(100_000) is True


# ── Anomaly detection (§3.4) ────────────────────────────────────────────────
def _established_profile(**overrides):
    base = dict(
        user_id=uuid4(),
        total_sessions=40,
        average_session_frequency_days=3.0,
        typical_bands={"evening": 0.6, "night": 0.3, "afternoon": 0.1},
    )
    base.update(overrides)
    return UserTemporalProfile(**base)


def test_no_anomaly_for_cold_start_profile():
    profile = UserTemporalProfile(user_id=uuid4(), total_sessions=2)
    detected, note = tr.detect_temporal_anomaly(CircadianBand.LATE_NIGHT, 99999, profile)
    assert detected is False
    assert note is None


def test_anomaly_atypical_band():
    profile = _established_profile()
    # late_night is absent from typical_bands → <5% → atypical.
    detected, note = tr.detect_temporal_anomaly(CircadianBand.LATE_NIGHT, 3 * 86400, profile)
    assert detected is True
    assert "atypical" in note.lower()


def test_anomaly_long_gap_beyond_baseline():
    profile = _established_profile()  # baseline 3 days → threshold 7.5 days
    detected, note = tr.detect_temporal_anomaly(
        CircadianBand.EVENING, 10 * 86400, profile
    )
    assert detected is True
    assert "days" in note.lower()


def test_anomaly_rapid_return():
    profile = _established_profile()
    detected, note = tr.detect_temporal_anomaly(
        CircadianBand.EVENING, 60, profile, shortest_recent_gap_seconds=3600
    )
    assert detected is True
    assert "rapid" in note.lower()


def test_no_anomaly_when_gap_within_own_historical_range():
    """A long-but-seen-before gap (§3.4 personalization) shouldn't fire condition 2."""
    profile = _established_profile(longest_historical_gap_days=12.0)  # baseline 3d, threshold 7.5d
    detected, note = tr.detect_temporal_anomaly(
        CircadianBand.EVENING, 10 * 86400, profile
    )
    assert detected is False
    assert note is None


def test_no_anomaly_for_typical_message():
    profile = _established_profile()
    detected, note = tr.detect_temporal_anomaly(
        CircadianBand.EVENING, 3 * 86400, profile, shortest_recent_gap_seconds=3600
    )
    assert detected is False
    assert note is None


# ── Fuzzy temporal labeling (§3.6) ──────────────────────────────────────────
@pytest.mark.parametrize(
    "delta,expected_substr",
    [
        (timedelta(minutes=5), "a moment ago"),
        (timedelta(hours=2), "earlier today"),
        (timedelta(days=2), "a couple of days ago"),
        (timedelta(days=5), "earlier this week"),
        (timedelta(days=10), "about a week ago"),
        (timedelta(days=20), "a few weeks ago"),
        (timedelta(days=45), "last month"),
        (timedelta(days=90), "a couple of months ago"),
        (timedelta(days=180), "a while back"),
        (timedelta(days=500), "about a year ago"),
    ],
)
def test_fuzzy_label_buckets(delta, expected_substr):
    now = datetime(2026, 6, 26, 15, 0, 0)
    labeler = tr.make_fuzzy_labeler(now)
    assert labeler(now - delta) == expected_substr


def test_fuzzy_label_same_day_boundary_applies_timezone_offset():
    """'earlier today' vs. 'yesterday' is a local-calendar-date question. At 2am IST (20:30 UTC
    the prior day), a memory from 10pm IST the previous evening (16:30 UTC, same UTC day) must
    read as 'yesterday' locally, not 'earlier today' from a raw-UTC same-day check."""
    now = datetime(2026, 6, 27, 20, 30)          # 2026-06-27 20:30 UTC == 2026-06-28 02:00 IST
    ts = now - timedelta(hours=4)                 # 2026-06-27 16:30 UTC == 2026-06-27 22:00 IST

    utc_labeler = tr.make_fuzzy_labeler(now)
    ist_labeler = tr.make_fuzzy_labeler(now, timezone_offset_hours=5.5)

    assert utc_labeler(ts) == "earlier today"     # same UTC calendar date
    assert ist_labeler(ts) == "yesterday"         # different IST calendar date


def test_fuzzy_label_eight_to_fourteen_months_uses_month_name():
    now = datetime(2026, 6, 26, 15, 0, 0)
    labeler = tr.make_fuzzy_labeler(now)
    label = labeler(now - timedelta(days=300))  # ~10 months → "back in <Month>"
    assert label.startswith("back in")


def test_fuzzy_label_two_years_uses_year():
    now = datetime(2026, 6, 26, 15, 0, 0)
    labeler = tr.make_fuzzy_labeler(now)
    target = now - timedelta(days=900)  # ~2.5 years
    assert labeler(target) == f"back in {target.year}"


def test_fuzzy_label_future_timestamp_is_clamped():
    now = datetime(2026, 6, 26, 15, 0, 0)
    labeler = tr.make_fuzzy_labeler(now)
    assert labeler(now + timedelta(hours=1)) == "a moment ago"
