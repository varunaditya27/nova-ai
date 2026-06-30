"""Integration: full System 1 turn — casual message → fast path → delivered response.

Verifies the orchestrator sequences Layers 11→1→2→13→3, routes a casual/simple message to the
System 1 generation path (Agent 4a only, Emotion Refiner skipped), always delivers via Layer 9,
and runs the post-turn state update last.
"""

from backend.pipeline.conversation_orchestrator import ConversationOrchestrator
from tests.integration.conftest import make_recording_steps


def test_casual_message_routes_to_system1():
    steps, rec = make_recording_steps()
    out = ConversationOrchestrator(steps).run_turn("u1", "hey what's up")
    assert out.cognitive_system == "system1"
    assert out.refined is False                       # Emotion Refiner (4b) skipped on fast path
    assert "L4a_plan" in rec.order and "L4b_refine" not in rec.order
    assert out.response_text == "factual draft"
    assert out.delivered is not None


def test_layer_sequence_is_correct():
    steps, rec = make_recording_steps()
    ConversationOrchestrator(steps).run_turn("u1", "hi")
    # Safety (Layer 11 SC-2) runs first and is never blocked
    assert rec.order[0] == "L11_safety"
    # perception → recall → cold-start overlay → classification, in order
    assert rec.order.index("L1_perceive") < rec.order.index("L2_recall") < rec.order.index("L3_classify")
    # delivery happens, then the post-turn state update is the final step
    assert rec.order.index("L9_deliver") < rec.order.index("state_update")
    assert rec.order[-1] == "state_update"
    assert rec.state_update_called is True


def test_empty_recall_sets_confabulation_guard():
    steps, rec = make_recording_steps(recall=lambda user_id, input_packet: [])
    out = ConversationOrchestrator(steps).run_turn("u1", "hi")
    assert out.confabulation_guard is True            # no memories → downstream must not invent


def test_nonempty_recall_clears_confabulation_guard():
    out = ConversationOrchestrator(make_recording_steps()[0]).run_turn("u1", "hi")
    assert out.confabulation_guard is False
