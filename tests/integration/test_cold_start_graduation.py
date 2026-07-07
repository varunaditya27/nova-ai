"""Integration: Layer 13 cold-start overlay wiring into the conversation pipeline.

Verifies that while cold start is active the orchestrator applies the overlay directives
(proactivity observe-only, reduced personality-drift gate) and surfaces a pending elicitation,
that a graduated user runs with no overlay, and that the real ColdStartEngine plugs into the
pipeline's `cold_start` step.
"""

from types import SimpleNamespace

from backend.layer13_onboarding import ColdStartEngine
from backend.pipeline.conversation_orchestrator import ConversationOrchestrator
from tests.integration.conftest import make_recording_steps


def _directives(pending=None):
    return SimpleNamespace(proactivity_mode="observe_only", personality_drift_gate=0.30,
                           pending_elicitation=pending)


def test_cold_start_overlay_applied_when_active():
    pending = SimpleNamespace(category="life_context", question="student or working?")
    steps, rec = make_recording_steps(cold_start=lambda u, m, sid="": _directives(pending))
    out = ConversationOrchestrator(steps).run_turn("u1", "exams have been rough")
    assert out.cold_start_active is True
    assert out.proactivity_mode == "observe_only"
    assert out.pending_elicitation is pending


def test_graduated_user_has_no_overlay():
    out = ConversationOrchestrator(make_recording_steps()[0]).run_turn("u1", "hi")
    assert out.cold_start_active is False
    assert out.pending_elicitation is None


def test_real_cold_start_engine_plugs_into_pipeline():
    # Wire the actual Layer 13 ColdStartEngine into the pipeline's cold_start step.
    engine = ColdStartEngine("u1")

    def cold_start_step(user_id, message, session_id=""):
        sctx = SimpleNamespace(recent_history=[], emotional_intensity=0.1, current_topic="",
                               active_triggers=set(), elicitation_count_this_session=0,
                               feature_triggers={}, user_has_shared_personally=False,
                               positive_engagement_session_count=0,
                               negative_surprise_events_detected=False, voluntary_return_count=0)
        engine.on_session_start(sctx)
        md = engine.on_message(message, sctx, timestamp=None)
        if not engine.active:
            return None
        return SimpleNamespace(
            proactivity_mode=engine.config.proactivity_mode,
            personality_drift_gate=engine.config.personality_drift_gate_multiplier,
            pending_elicitation=md.pending_elicitation_question)

    steps, rec = make_recording_steps(cold_start=cold_start_step)
    out = ConversationOrchestrator(steps).run_turn("u1", "hi, I'm Sam")
    assert out.cold_start_active is True
    assert out.proactivity_mode == "observe_only"
    assert engine.state.user_handle == "Sam"          # real L13 passive extraction ran
