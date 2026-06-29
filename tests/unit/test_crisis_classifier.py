"""Tests for SC-2 Crisis Detection Engine (architecture doc §4)."""

from datetime import date, timedelta
from types import SimpleNamespace

from backend.layer11_safety import crisis_classifier as cc
from backend.layer11_safety.schemas import CrisisSignal, CrisisTier, SemanticClassifierResult

NOW = date(2025, 6, 1)


def _evaluate(message, semantic_fn=None, episodic=None, emotional=None):
    return cc.evaluate(message, recent_history=[], episodic_memories=episodic or [],
                       emotional_records=emotional or [], semantic_fn=semantic_fn, now=NOW)


# ── Layer 1: lexical (§4.3) ──────────────────────────────────────────────────
def test_tier1_explicit_intent():
    sig = _evaluate("i'm going to kill myself tonight")
    assert sig.tier == CrisisTier.TIER_1.value and "lexical" in sig.detection_layers_fired


def test_tier2_passive_ideation():
    sig = _evaluate("honestly everyone would be better off without me")
    assert sig.tier == CrisisTier.TIER_2.value


def test_tier3_burden_language():
    sig = _evaluate("i just feel like a burden to everyone")
    assert sig.tier == CrisisTier.TIER_3.value


def test_figurative_is_not_crisis():
    sig = _evaluate("ugh i want to kill this bug in my code")
    assert sig.tier == CrisisTier.NONE.value


# ── Layer 2: semantic (§4.3) ─────────────────────────────────────────────────
def test_semantic_fires_when_lexical_silent():
    fn = lambda msg, ctx: SemanticClassifierResult(tier=CrisisTier.TIER_2.value, confidence=0.85)
    sig = _evaluate("i don't really see the way forward anymore", semantic_fn=fn)
    assert sig.tier == CrisisTier.TIER_2.value and "semantic" in sig.detection_layers_fired


def test_semantic_below_threshold_ignored():
    fn = lambda msg, ctx: SemanticClassifierResult(tier=CrisisTier.TIER_2.value, confidence=0.50)
    sig = _evaluate("just a bit down today", semantic_fn=fn)
    assert sig.tier == CrisisTier.NONE.value


def test_fusion_takes_highest_tier():
    # lexical → tier_3 (burden), semantic → tier_1; final must be tier_1.
    fn = lambda msg, ctx: SemanticClassifierResult(tier=CrisisTier.TIER_1.value, confidence=0.9)
    sig = _evaluate("i feel like a burden", semantic_fn=fn)
    assert sig.tier == CrisisTier.TIER_1.value


# ── Layer 3: longitudinal (§4.3) ─────────────────────────────────────────────
def test_longitudinal_pattern_raises_tier3():
    # frequency 0.5 (2 of 4 distress-tagged), gentle valence decline, isolation_count 2 → Tier 3.
    episodic = [SimpleNamespace(date=NOW - timedelta(days=2), topics=["hopelessness", "isolation"]),
                SimpleNamespace(date=NOW - timedelta(days=6), topics=["isolation"]),
                SimpleNamespace(date=NOW - timedelta(days=12), topics=["work"]),
                SimpleNamespace(date=NOW - timedelta(days=20), topics=["hobbies"])]
    emotional = [SimpleNamespace(date=NOW - timedelta(days=d), valence=v)
                 for d, v in [(25, 0.1), (20, 0.05), (12, -0.15), (6, -0.25), (2, -0.3)]]
    sig = cc.evaluate("just checking in", recent_history=[], episodic_memories=episodic,
                      emotional_records=emotional, semantic_fn=None, now=NOW)
    assert sig.tier == CrisisTier.TIER_3.value and "longitudinal" in sig.detection_layers_fired


# ── Signal metadata (§4.2) ───────────────────────────────────────────────────
def test_tier1_is_immediately_actionable():
    assert _evaluate("i have pills to end my life").immediately_actionable is True


def test_tier3_is_not_immediately_actionable():
    assert _evaluate("i feel like a burden").immediately_actionable is False


def test_recommended_action_for_tier1():
    assert _evaluate("i'm going to kill myself").recommended_action == "full_crisis_response"


def test_no_crisis_returns_signal_object():
    sig = _evaluate("had a nice walk today")
    assert isinstance(sig, CrisisSignal) and sig.tier == CrisisTier.NONE.value
    assert sig.recommended_action == "no_action"


def test_false_positive_risk_is_inverse_of_confidence():
    sig = _evaluate("i'm going to kill myself")
    assert abs(sig.false_positive_risk - (1.0 - sig.confidence)) < 1e-9
