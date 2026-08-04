"""Integration: full System 2 turn — emotional/complex message → full path.

Verifies that an emotionally-weighted or complex message routes to System 2, which runs both
Agent 4a (Semantic Planner) and Agent 4b (Emotion Refiner), then delivers and updates state.
"""

from types import SimpleNamespace

from backend.pipeline.conversation_orchestrator import ConversationOrchestrator
from tests.integration.conftest import make_recording_steps


def _classify(mode="emotional_support", complexity="complex", crisis=False):
    return lambda message, input_packet, recalled: SimpleNamespace(
        crisis_active=crisis, conversation_mode=mode, complexity=complexity)


def test_emotional_message_routes_to_system2():
    steps, rec = make_recording_steps(classify=_classify(mode="emotional_support"))
    out = ConversationOrchestrator(steps).run_turn("u1", "I've been really overwhelmed lately")
    assert out.cognitive_system == "system2"
    assert out.refined is True
    assert "L4a_plan" in rec.order and "L4b_refine" in rec.order
    assert out.response_text == "refined(factual draft)"


def test_complex_message_routes_to_system2_even_if_casual_mode():
    steps, rec = make_recording_steps(classify=_classify(mode="casual", complexity="complex"))
    out = ConversationOrchestrator(steps).run_turn("u1", "explain how compound interest works")
    assert out.cognitive_system == "system2"
    assert "L4b_refine" in rec.order


def test_system2_runs_persona_before_planning():
    steps, rec = make_recording_steps(classify=_classify())
    ConversationOrchestrator(steps).run_turn("u1", "help me think this through")
    assert rec.order.index("L4_persona") < rec.order.index("L4a_plan") < rec.order.index("L4b_refine")
    assert rec.order.index("L4b_refine") < rec.order.index("L9_deliver")
