"""Integration: Layer 11 safety override and post-generation guardrails.

Verifies the crisis veto (SC-2 detection → SC-3 escalation replaces the normal response entirely,
generation is skipped, Layer 9 delivers in crisis mode with micro-interactions suppressed), the
OR-semantics between SC-2 and the Layer 3 crisis flag, the post-generation ethical guardrail
rewrite (SC-1), and the invariant that the safety scan is never blocked by a downstream failure.
"""

from types import SimpleNamespace

from backend.pipeline.conversation_orchestrator import ConversationOrchestrator
from tests.integration.conftest import make_recording_steps


def test_crisis_vetoes_normal_generation():
    steps, rec = make_recording_steps(
        safety_scan=lambda u, m, p: SimpleNamespace(is_crisis=True, tier="tier_3"))
    out = ConversationOrchestrator(steps).run_turn("u1", "I don't want to be here anymore")
    assert out.crisis_active is True and out.crisis_tier == "tier_3"
    # SC-3 escalation replaces the response; normal generation is skipped entirely
    assert "L11_escalate" in rec.order
    assert "L4a_plan" not in rec.order and "L4b_refine" not in rec.order
    assert "988" in out.response_text
    # Layer 9 still runs, in crisis mode (pure prose, micro-interactions suppressed)
    assert rec.deliver_crisis_mode is True
    assert "L9_deliver" in rec.order


def test_layer3_crisis_flag_also_triggers_override():
    # SC-2 says no, but Layer 3 raised the crisis flag → OR-semantics still escalates.
    steps, rec = make_recording_steps(
        classify=lambda m, p, r: SimpleNamespace(crisis_active=True, conversation_mode="emotional_support",
                                                 complexity="complex"))
    out = ConversationOrchestrator(steps).run_turn("u1", "everything feels pointless")
    assert out.crisis_active is True
    assert "L11_escalate" in rec.order and "L4a_plan" not in rec.order


def test_safety_scan_runs_first_and_is_never_blocked():
    def boom(message, input_packet, recalled):
        raise RuntimeError("classifier exploded")
    steps, rec = make_recording_steps(classify=boom)
    out = ConversationOrchestrator(steps).run_turn("u1", "hi")
    # safety ran before the failure, and the turn still produced a (degraded) delivered output
    assert rec.order[0] == "L11_safety"
    assert out.delivered is not None
    assert out.degraded is True


def test_post_generation_guardrail_rewrites_response():
    steps, rec = make_recording_steps(
        guardrails=lambda ctx, resp: SimpleNamespace(
            approved=False, replacement="[redacted: safer rephrasing]", flags=["pii"]))
    out = ConversationOrchestrator(steps).run_turn("u1", "tell me something")
    assert out.response_text == "[redacted: safer rephrasing]"
    assert out.guardrail_flags == ["pii"]
    assert rec.delivered_text == "[redacted: safer rephrasing]"   # the rewritten text is delivered
