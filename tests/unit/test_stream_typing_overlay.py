"""Tests for SC-1 Stream Typing Overlay (architecture doc §3.2)."""

from backend.layer9_output.stream_typing_overlay import StreamTypingOverlay
from backend.layer9_output.schemas import TypingEventType


class _Rng:
    """Deterministic rng: gauss returns the mean (no noise)."""
    def gauss(self, mu, sigma):
        return mu


def _emit(token="word", prev="word", mode="casual_chat", circadian="afternoon"):
    return StreamTypingOverlay().emit_token(token, prev, mode, circadian, rng=_Rng())


def test_emit_returns_token_event_with_delay():
    events = _emit()
    token_events = [e for e in events if e.event_type == TypingEventType.TOKEN.value]
    assert len(token_events) == 1 and token_events[0].delay_before_ms > 0
    assert token_events[0].token == "word"


def test_emotional_support_slower_than_casual():
    casual = _emit(mode="casual_chat")[-1].delay_before_ms
    emotional = _emit(mode="emotional_support")[-1].delay_before_ms
    assert emotional > casual


def test_late_night_slows_typing():
    night = _emit(circadian="late_night")[-1].delay_before_ms
    day = _emit(circadian="afternoon")[-1].delay_before_ms
    assert night > day


def test_morning_speeds_typing():
    morning = _emit(circadian="morning")[-1].delay_before_ms
    day = _emit(circadian="afternoon")[-1].delay_before_ms
    assert morning < day


def test_sentence_boundary_inserts_pause_before_token():
    events = _emit(token="Next", prev=".")
    assert events[0].event_type == TypingEventType.PAUSE.value
    assert any(e.event_type == TypingEventType.TOKEN.value for e in events)


def test_delay_never_below_floor():
    # Even an aggressive negative-noise rng can't push the delay below the 20ms floor.
    class _NegRng:
        def gauss(self, mu, sigma):
            return -5.0
    events = StreamTypingOverlay().emit_token("x", "x", "technical", "afternoon", rng=_NegRng())
    assert events[-1].delay_before_ms >= 20


def test_unknown_mode_falls_back():
    events = _emit(mode="nonexistent_mode")
    assert events[-1].delay_before_ms > 0
