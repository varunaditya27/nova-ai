"""Tests for the Safety Agent coordinator (architecture doc §7)."""

from types import SimpleNamespace

from backend.layer11_safety.safety_agent import SafetyAgent
from backend.layer11_safety.schemas import CrisisTier, SafetyAgentDecision


def _ctx(**kw):
    return SimpleNamespace(user_id="u1", session_id="s1", has_real_deadline=False,
                           vulnerability_score=0.0, **kw)


def _agent():
    return SafetyAgent(region="india")


# ── Veto authority on crisis (§7) ────────────────────────────────────────────
def test_tier1_vetoes_pipeline_with_crisis_response():
    out = _agent().process_incoming_message(
        "i'm going to kill myself tonight", session_context=_ctx(),
        proposed_response="Anyway, about your project deadline...")
    assert isinstance(out, SafetyAgentDecision)
    assert out.veto_main_pipeline is True
    assert out.crisis_signal.tier == CrisisTier.TIER_1.value
    assert out.injected_response and "9152987821" in out.injected_response


def test_tier2_vetoes_pipeline():
    out = _agent().process_incoming_message(
        "everyone would be better off without me", session_context=_ctx(),
        proposed_response="ok")
    assert out.veto_main_pipeline is True and out.crisis_signal.tier == CrisisTier.TIER_2.value


def test_injected_crisis_response_is_safe_mode_prose():
    out = _agent().process_incoming_message(
        "i have pills to end my life", session_context=_ctx(), proposed_response="x")
    assert "##" not in out.injected_response and "**" not in out.injected_response


# ── Normal path → guardrail filtering (§7) ───────────────────────────────────
def test_clean_response_passes_through():
    out = _agent().process_incoming_message(
        "what's a good recipe for dinner?", session_context=_ctx(),
        proposed_response="How about a simple pasta? Here's one way to do it.")
    assert out.veto_main_pipeline is False
    assert out.final_response == "How about a simple pasta? Here's one way to do it."


def test_manipulative_proposed_response_is_replaced():
    out = _agent().process_incoming_message(
        "i might take a break from chatting", session_context=_ctx(),
        proposed_response="You can't stop talking to me, no one else understands you.")
    assert out.veto_main_pipeline is False
    assert out.guardrail_result.passed is False
    assert out.final_response != "You can't stop talking to me, no one else understands you."


# ── Tier 3 → monitoring, pipeline proceeds (§7) ──────────────────────────────
def test_tier3_does_not_veto_but_sets_monitoring():
    out = _agent().process_incoming_message(
        "i just feel like a burden lately", session_context=_ctx(), proposed_response="I hear you.")
    assert out.veto_main_pipeline is False
    assert out.crisis_signal.tier == CrisisTier.TIER_3.value
    assert out.crisis_mode_state is not None


# ── Audit logging (§8) ───────────────────────────────────────────────────────
def test_crisis_event_is_logged_to_safety_record():
    agent = _agent()
    agent.process_incoming_message("i'm going to kill myself", session_context=_ctx(),
                                   proposed_response="x")
    assert len(agent.record.entries) >= 1 and agent.record.verify_chain() is True


def test_guardrail_violation_is_logged():
    agent = _agent()
    agent.process_incoming_message("hi", session_context=_ctx(),
                                   proposed_response="I love you and I need you.")
    types = [e.entry_type for e in agent.record.entries]
    assert any("guardrail" in t for t in types)
