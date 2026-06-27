"""Tests for the Memory Strength decay model (architecture doc §8.3)."""

import math

from backend.layer2_memory import memory_strength as ms


def test_initial_strength_weighted_sum():
    # S0 = 0.5*base + 0.3*emotional + 0.2*novelty
    assert ms.initial_strength(base_importance=0.8, emotional_weight=0.5,
                               novelty=0.4) == ms_expected(0.8, 0.5, 0.4)


def ms_expected(b, e, n):
    return 0.5 * b + 0.3 * e + 0.2 * n


def test_decay_rate_scales_inversely_with_importance():
    # λ = base_decay * (1 - importance); base_decay default 0.10
    assert ms.decay_rate(importance=0.0) == 0.10
    assert ms.decay_rate(importance=1.0) == 0.0
    assert ms.decay_rate(importance=0.5) == 0.05


def test_high_importance_decays_slower():
    low = ms.decayed_strength(S0=1.0, decay_rate=ms.decay_rate(0.2), t_days=30)
    high = ms.decayed_strength(S0=1.0, decay_rate=ms.decay_rate(0.9), t_days=30)
    assert high > low


def test_decayed_strength_formula():
    lam = 0.05
    assert math.isclose(ms.decayed_strength(1.0, lam, 10), math.exp(-0.5), rel_tol=1e-9)


def test_decayed_strength_at_zero_time_is_s0():
    assert ms.decayed_strength(0.7, 0.1, 0) == 0.7


def test_reinforce_logarithmic_returns():
    # S_new = S_old + log(1 + signal)
    assert math.isclose(ms.reinforce(0.5, 1.0), 0.5 + math.log(2), rel_tol=1e-9)


def test_reinforce_diminishing():
    first = ms.reinforce(0.0, 1.0) - 0.0
    # a second unit of signal on top adds the same log(2) increment, but total stays bounded
    assert first == math.log(2)


def test_deletion_decision_delete_when_weak_and_unimportant():
    assert ms.deletion_decision(S_current=0.05, importance=0.3) == "delete"


def test_deletion_decision_archive_when_weak_but_important():
    assert ms.deletion_decision(S_current=0.05, importance=0.6) == "archive"


def test_deletion_decision_keep_when_strong():
    assert ms.deletion_decision(S_current=0.4, importance=0.3) == "keep"


def test_deletion_boundary_exactly_threshold_keeps():
    # S(t) < 0.1 is the trigger; exactly 0.1 is not below threshold → keep
    assert ms.deletion_decision(S_current=0.1, importance=0.2) == "keep"
