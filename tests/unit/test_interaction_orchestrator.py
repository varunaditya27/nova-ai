"""Tests for SC-1 Interaction Orchestrator + Layer 9 engine (architecture doc §3.5, §7, §8)."""

from backend.layer9_output import delivery
from backend.layer9_output import interaction_orchestrator as io
from backend.layer9_output.schemas import (
    AudioResult,
    Layer9Output,
    MicroInteractionPlan,
    OrchestratedOutput,
    SelfEditPlan,
    Structure,
    TypingEventType,
    UserFormatProfile,
)


class _Rng:
    """Deterministic rng supporting every method the SCs use."""
    def randint(self, a, b):
        return (a + b) // 2
    def random(self):
        return 0.99            # suppress probabilistic self-edit by default
    def uniform(self, a, b):
        return (a + b) / 2
    def gauss(self, mu, sigma):
        return mu
    def choice(self, seq):
        return seq[0]


class _Backend:
    def synthesize(self, ssml_text, voice_id=None):
        return AudioResult(audio_bytes=b"A", ok=True)


def _types(output):
    return [e.event_type for e in output.events]


# ── Event assembly (§3.5) ────────────────────────────────────────────────────
def test_orchestrate_ends_with_send_message():
    out = io.orchestrate_output("Hello there friend.", conversation_mode="casual_chat", rng=_Rng())
    assert isinstance(out, OrchestratedOutput)
    assert out.events[-1].event_type == TypingEventType.SEND_MESSAGE.value
    assert out.final_message_text == "Hello there friend."


def test_thinking_pause_event_present_when_requested():
    out = io.orchestrate_output("Hi.", conversation_mode="casual_chat",
                                thinking_pause_ms=1200, rng=_Rng())
    assert TypingEventType.THINKING_PAUSE.value in _types(out)


def test_backchannel_event_when_acknowledgment_planned():
    plan = MicroInteractionPlan(acknowledgment="I hear that.")
    out = io.orchestrate_output("Okay.", conversation_mode="casual_chat",
                                micro_plan=plan, rng=_Rng())
    assert TypingEventType.BACKCHANNEL.value in _types(out)
    assert out.backchannel_text == "I hear that."


def test_token_events_present_for_response():
    out = io.orchestrate_output("one two three", conversation_mode="casual_chat", rng=_Rng())
    assert _types(out).count(TypingEventType.TOKEN.value) >= 3


def test_self_edit_inserts_show_and_delete_events():
    plan = SelfEditPlan(phrase_to_show_then_delete="actually never mind",
                        insert_after_chars=4, deletion_pause_ms=500, resume_pause_ms=400)
    out = io.orchestrate_output("one two three four", conversation_mode="casual_chat",
                                self_edit_plan=plan, rng=_Rng())
    assert TypingEventType.SHOW_PHRASE.value in _types(out)
    assert TypingEventType.DELETE_PHRASE.value in _types(out)


def test_closing_signal_replaces_response():
    plan = MicroInteractionPlan(closing_signal="Take care.")
    out = io.orchestrate_output("whatever the draft was", conversation_mode="casual_chat",
                                micro_plan=plan, rng=_Rng())
    assert out.final_message_text == "Take care."


# ── Engine integration (§7, §8) ──────────────────────────────────────────────
def _deliver(text="I think that could really work out well.", **kw):
    return delivery.deliver(text, conversation_mode=kw.pop("mode", "casual_chat"),
                      user_format_profile=UserFormatProfile(user_id="u1"), rng=_Rng(), **kw)


def test_deliver_returns_layer9_output():
    out = _deliver()
    assert isinstance(out, Layer9Output)
    assert out.final_message_text
    assert out.format_spec_applied is not None
    assert out.orchestrated_output is not None


def test_deliver_crisis_forces_pure_prose_and_no_micro_interactions():
    out = _deliver(text="## Heading\n- bullet\n**bold**", mode="crisis_support",
                   crisis_mode_active=True, emotional_intensity=0.9)
    assert out.format_spec_applied.structure == Structure.PURE_PROSE.value
    assert "##" not in out.final_message_text and "**" not in out.final_message_text
    assert out.micro_interaction_plan.any_pre_response_signal is False
    assert out.total_orchestration_time_ms >= 0


def test_deliver_voice_mode_populates_audio():
    out = _deliver(voice_mode=True, tts_backend=_Backend())
    assert out.voice_mode is True
    assert out.audio_result is not None and out.audio_result.ok is True
    assert out.ssml_document is not None


def test_deliver_voice_without_backend_is_graceful():
    out = _deliver(voice_mode=True, tts_backend=None)
    assert out.final_message_text                      # text still delivered
    assert out.audio_result is None or out.audio_result.ok is False
