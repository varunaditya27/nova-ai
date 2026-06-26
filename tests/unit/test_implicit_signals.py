"""Tests for Layer 1 SC-2 — Implicit Signal Extractor (architecture doc §4).

Behavioral metadata of *how* a message was sent: latency, deletion, length deviation,
initiation type, burst — aggregated into the implicit_emotional_intensity_score (§4.7).
"""

from datetime import datetime, timedelta

import pytest

from backend.layer1_input import implicit_signals as isig
from backend.layer1_input.schemas import InitiationType, LatencySignal

T0 = datetime(2026, 6, 26, 12, 0, 0)


# ── Latency (§4.2) ───────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "ms,expected",
    [
        (0, LatencySignal.REACTIVE), (2999, LatencySignal.REACTIVE),
        (3000, LatencySignal.QUICK), (14999, LatencySignal.QUICK),
        (15000, LatencySignal.CONSIDERED), (59999, LatencySignal.CONSIDERED),
        (60000, LatencySignal.REFLECTIVE), (299999, LatencySignal.REFLECTIVE),
        (300000, LatencySignal.DELAYED), (1199999, LatencySignal.DELAYED),
        (1200000, LatencySignal.BREAK), (5_000_000, LatencySignal.BREAK),
    ],
)
def test_classify_latency_boundaries(ms, expected):
    assert isig.classify_latency(ms) == expected


def test_classify_latency_none_when_missing():
    assert isig.classify_latency(None) is None


def test_compute_latency_from_typing_start():
    nova = T0
    typing = T0 + timedelta(seconds=8)
    assert isig.compute_latency(nova, typing, T0 + timedelta(seconds=30)) == 8000


def test_compute_latency_falls_back_to_received_at():
    nova = T0
    received = T0 + timedelta(seconds=12)
    assert isig.compute_latency(nova, None, received) == 12000


def test_compute_latency_none_without_prior_nova_message():
    assert isig.compute_latency(None, T0, T0) is None


def test_latency_deviation_ratio():
    assert isig.latency_deviation(2000, 1000.0) == 2.0
    assert isig.latency_deviation(2000, None) is None
    assert isig.latency_deviation(None, 1000.0) is None


# ── Deletion (§4.3) ──────────────────────────────────────────────────────────
def test_deletion_ratio():
    assert isig.deletion_ratio(100, 20) == pytest.approx(0.2)
    assert isig.deletion_ratio(0, 0) is None  # no draft activity


# ── Length distribution (§4.4) ───────────────────────────────────────────────
def test_length_ratio_against_baseline():
    assert isig.length_ratio(160, 80.0) == 2.0


def test_length_ratio_defaults_to_one_without_baseline():
    assert isig.length_ratio(160, None) == 1.0
    assert isig.length_ratio(160, 0.0) == 1.0


# ── Initiation type (§4.5) ───────────────────────────────────────────────────
def test_initiation_continuation_when_session_ongoing():
    assert (
        isig.resolve_initiation_type(is_continuation=True, is_reply_to_proactive=False,
                                     last_was_proactive=False)
        == InitiationType.CONTINUATION
    )


def test_initiation_response_to_checkin():
    assert (
        isig.resolve_initiation_type(is_continuation=False, is_reply_to_proactive=True,
                                     last_was_proactive=True)
        == InitiationType.RESPONSE_TO_CHECKIN
    )


def test_initiation_hot_after_recent_proactive():
    assert (
        isig.resolve_initiation_type(is_continuation=False, is_reply_to_proactive=False,
                                     last_was_proactive=True)
        == InitiationType.USER_INITIATED_HOT
    )


def test_initiation_cold_by_default():
    assert (
        isig.resolve_initiation_type(is_continuation=False, is_reply_to_proactive=False,
                                     last_was_proactive=False)
        == InitiationType.USER_INITIATED_COLD
    )


# ── Implicit emotional intensity score (§4.7, verbatim formula) ──────────────
def test_intensity_neutral_message_is_zero():
    score = isig.compute_implicit_emotional_intensity(
        latency_signal="considered", deletion_occurred=False, deletion_count=0,
        length_ratio=1.0, initiation_type="continuation",
    )
    assert score == 0.0


def test_intensity_reactive_cold_open():
    score = isig.compute_implicit_emotional_intensity(
        latency_signal="reactive", deletion_occurred=False, deletion_count=0,
        length_ratio=1.0, initiation_type="user_initiated_cold",
    )
    # 0.25*0.6 (reactive) + 0.10 (cold) = 0.25
    assert score == pytest.approx(0.25)


def test_intensity_long_venting_message():
    score = isig.compute_implicit_emotional_intensity(
        latency_signal="considered", deletion_occurred=False, deletion_count=0,
        length_ratio=8.0, initiation_type="continuation",
    )
    # length contribution: 0.25 * min((8-4)/4, 1) = 0.25
    assert score == pytest.approx(0.25)


def test_intensity_self_censorship_deletions():
    score = isig.compute_implicit_emotional_intensity(
        latency_signal="considered", deletion_occurred=True, deletion_count=5,
        length_ratio=1.0, initiation_type="continuation",
    )
    # deletion contribution: 0.20 * min(5/5, 1) = 0.20
    assert score == pytest.approx(0.20)


def test_intensity_withdrawal_short_message():
    score = isig.compute_implicit_emotional_intensity(
        latency_signal="considered", deletion_occurred=False, deletion_count=0,
        length_ratio=0.1, initiation_type="continuation",
    )
    assert score == pytest.approx(0.20)


def test_intensity_reaches_formula_ceiling():
    # The §4.7 weights cap the score at 0.70 (0.15 latency + 0.20 deletion + 0.25
    # length + 0.10 initiation); the min(score, 1.0) clamp is a defensive guard that
    # never actually fires. Maxed-out inputs must therefore land at exactly 0.70.
    score = isig.compute_implicit_emotional_intensity(
        latency_signal="reactive", deletion_occurred=True, deletion_count=10,
        length_ratio=20.0, initiation_type="user_initiated_cold",
    )
    assert score == pytest.approx(0.70)


# ── Burst (§4.6) ─────────────────────────────────────────────────────────────
def test_is_message_burst_requires_multiple_messages():
    assert isig.is_message_burst(is_burst=True, burst_count=3) is True
    assert isig.is_message_burst(is_burst=True, burst_count=1) is False
    assert isig.is_message_burst(is_burst=False, burst_count=3) is False
