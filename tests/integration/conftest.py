"""Shared fakes for pipeline integration tests.

The pipeline is *pure orchestration* (zero business logic) — its contract is the sequence in
which it calls the 13 layers, plus the cross-cutting invariants (Layer 11 crisis veto, Layer 13
cold-start overlay, System 1/2 routing, post-turn state update, confabulation guard). Each layer's
internal behaviour is already covered by the unit suite, so here we inject lightweight recording
fakes for every layer step and assert the orchestration contract.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.pipeline.conversation_orchestrator import PipelineSteps


def make_recording_steps(**overrides):
    """Return (steps, rec). `rec.order` records the layer call sequence; override any step."""
    rec = SimpleNamespace(order=[], deliver_crisis_mode=None, state_update_called=False,
                          delivered_text=None)

    def perceive(user_id, message, now, session_id=""):
        rec.order.append("L1_perceive"); return {"perceived_message": message}

    def recall(user_id, input_packet):
        rec.order.append("L2_recall"); return [{"id": "m1", "text": "prior memory"}]

    def cold_start(user_id, message, session_id=""):
        rec.order.append("L13_coldstart"); return None        # graduated by default

    def classify(message, input_packet, recalled):
        rec.order.append("L3_classify")
        return SimpleNamespace(crisis_flag=False, mode="casual", complexity="simple")

    def safety_scan(user_id, message, input_packet):
        rec.order.append("L11_safety")
        return SimpleNamespace(is_crisis=False, tier=None)

    def build_persona(ctx):
        rec.order.append("L4_persona"); return {"warmth": 0.75}

    def plan(ctx):
        rec.order.append("L4a_plan"); return "factual draft"

    def refine(ctx, draft):
        rec.order.append("L4b_refine"); return f"refined({draft})"

    def guardrails(ctx, response):
        rec.order.append("L11_guardrails")
        return SimpleNamespace(approved=True, replacement=None, flags=[])

    def escalate(ctx, crisis):
        rec.order.append("L11_escalate")
        return "I'm really glad you told me. You can reach a crisis line at 988."

    def deliver(ctx, response_text, crisis_mode_active):
        rec.order.append("L9_deliver")
        rec.deliver_crisis_mode = crisis_mode_active
        rec.delivered_text = response_text
        return {"text": response_text, "crisis_mode": crisis_mode_active}

    def state_update(ctx):
        rec.order.append("state_update"); rec.state_update_called = True

    defaults = dict(perceive=perceive, recall=recall, cold_start=cold_start, classify=classify,
                    safety_scan=safety_scan, build_persona=build_persona, plan=plan, refine=refine,
                    guardrails=guardrails, escalate=escalate, deliver=deliver,
                    state_update=state_update)
    defaults.update(overrides)
    return PipelineSteps(**defaults), rec


@pytest.fixture
def steps_and_rec():
    return make_recording_steps()
