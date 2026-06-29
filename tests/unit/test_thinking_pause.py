"""Tests for SC-1 Thinking Pause (architecture doc §3.3, §4.2)."""

from backend.layer9_output import thinking_pause as tp


class _FakeRng:
    """Deterministic rng: randint returns the midpoint of the range."""
    def randint(self, a, b):
        return (a + b) // 2


def _pause(complexity=0.6, emotion=0.5, urgency=0.0, circadian="afternoon",
           mode="casual_chat", stage="friend", crisis=False):
    return tp.compute_thinking_pause(
        complexity_score=complexity, emotional_intensity=emotion, urgency_level=urgency,
        circadian_band=circadian, conversation_mode=mode, relationship_stage=stage,
        crisis_mode_active=crisis, rng=_FakeRng())


def test_crisis_mode_has_no_pause():
    assert _pause(crisis=True) == 0


def test_high_urgency_skips_pause():
    assert _pause(urgency=0.9) == 0


def test_trivial_response_has_no_pause():
    assert _pause(complexity=0.2, emotion=0.2) == 0


def test_moderate_pause_in_reasonable_band():
    assert 700 <= _pause(complexity=0.6, emotion=0.5) <= 1600


def test_deep_question_pauses_longer_than_light():
    light = _pause(complexity=0.45, emotion=0.5)
    deep = _pause(complexity=0.9, emotion=0.9)
    assert deep > light


def test_stranger_reduces_visible_hesitation():
    assert _pause(stage="stranger") < _pause(stage="friend")


def test_late_night_lengthens_pause():
    assert _pause(circadian="late_night") > _pause(circadian="afternoon")


def test_morning_shortens_pause():
    assert _pause(circadian="morning") < _pause(circadian="afternoon")


# ── Thinking indicator gate (§4.2) ───────────────────────────────────────────
def test_thinking_indicator_fires_on_high_complexity():
    assert tp.should_show_thinking_indicator(0.7, 0.3, "deep_reasoning") is True


def test_thinking_indicator_disabled_in_technical():
    assert tp.should_show_thinking_indicator(0.9, 0.9, "technical") is False
