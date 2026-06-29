"""Tests for SC-3 Escalation Protocol (architecture doc §5)."""

from backend.layer11_safety import escalation_engine as ee
from backend.layer11_safety.schemas import CrisisModeConstraints, CrisisResponse, CrisisTier


# ── Resource registry (§10) ──────────────────────────────────────────────────
def test_resources_localized_to_region():
    india = ee.get_resources_for_region("india")
    us = ee.get_resources_for_region("us")
    assert "iCall" in india and "988 Suicide & Crisis Lifeline" in us


def test_unknown_region_falls_back_to_international():
    res = ee.get_resources_for_region("atlantis")
    assert res  # non-empty international fallback


# ── Tier 1 response (§5.3) ───────────────────────────────────────────────────
def test_tier1_response_is_prose_and_includes_regional_resource():
    r = ee.generate_crisis_response(CrisisTier.TIER_1.value, region="india")
    assert isinstance(r, CrisisResponse)
    assert "9152987821" in r.text            # iCall number from the registry
    assert "\n-" not in r.text and "#" not in r.text  # prose only, no lists/headers


def test_tier1_leads_with_acknowledgment_not_disclaimer():
    r = ee.generate_crisis_response(CrisisTier.TIER_1.value, region="india")
    assert not r.text.lower().startswith("i'm an ai")
    assert not r.text.strip()[0].isdigit()   # does not open with a phone number


def test_tier1_resources_offered_populated():
    r = ee.generate_crisis_response(CrisisTier.TIER_1.value, region="india")
    assert r.resources_offered                # non-empty


# ── Tier 2 response (§5.4) ───────────────────────────────────────────────────
def test_tier2_response_offers_resources_gently():
    r = ee.generate_crisis_response(CrisisTier.TIER_2.value, region="us")
    assert "988" in r.text
    assert r.tier == CrisisTier.TIER_2.value


# ── Constraints (§5.2) ───────────────────────────────────────────────────────
def test_response_carries_crisis_mode_constraints():
    r = ee.generate_crisis_response(CrisisTier.TIER_1.value, region="india")
    assert isinstance(r.constraints, CrisisModeConstraints)
    assert r.constraints.response_format == "prose_only"
    assert r.constraints.resource_provision_required is True


# ── LLM acknowledgment, registry resources (anti-hallucination) ──────────────
def test_llm_writes_acknowledgment_resources_still_from_registry():
    # Even when the LLM acknowledgment omits any number, the registry number is injected.
    r = ee.generate_crisis_response(CrisisTier.TIER_1.value, region="india",
                                    llm_fn=lambda prompt: "I'm right here with you.")
    assert "I'm right here with you." in r.text
    assert "9152987821" in r.text             # number never comes from the LLM
    assert r.used_fallback is False


def test_static_fallback_without_llm_still_has_resource():
    r = ee.generate_crisis_response(CrisisTier.TIER_1.value, region="india", llm_fn=None)
    assert r.used_fallback is True and "9152987821" in r.text


def test_llm_failure_falls_back_safely():
    def boom(prompt):
        raise RuntimeError("llm down")
    r = ee.generate_crisis_response(CrisisTier.TIER_1.value, region="india", llm_fn=boom)
    assert r.text and "9152987821" in r.text  # never empty for Tier 1
