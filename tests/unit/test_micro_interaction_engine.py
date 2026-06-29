"""Tests for SC-2 Micro-Interaction Engine (architecture doc §4.2-§4.3)."""

from backend.layer9_output import micro_interaction_engine as mie
from backend.layer9_output.schemas import MicroInteractionPlan


class _Rng:
    """Deterministic rng: choice picks the first option."""
    def choice(self, seq):
        return seq[0]


def _plan(mode="casual_chat", stage="friend", intensity=0.2, turn="casual",
          user_len=0, consecutive=0, complexity=0.0, since_ack=99,
          correction=False, proactive=False, farewell=False, crisis=False):
    return mie.plan_micro_interactions(
        conversation_mode=mode, relationship_stage=stage, emotional_intensity=intensity,
        turn_type=turn, user_message_length=user_len, consecutive_user_messages=consecutive,
        complexity_score=complexity, messages_since_last_ack=since_ack,
        correction_armed=correction, is_proactive=proactive, farewell_detected=farewell,
        crisis_mode_active=crisis, rng=_Rng())


# ── Crisis hard override (§2) ────────────────────────────────────────────────
def test_crisis_suppresses_all_micro_interactions():
    p = _plan(crisis=True, user_len=900, intensity=0.9, proactive=True, farewell=True)
    assert isinstance(p, MicroInteractionPlan)
    assert p.acknowledgment is None and p.emotional_prefix is None
    assert p.transition_phrase is None and p.closing_signal is None
    assert p.any_pre_response_signal is False


# ── Type 1: Acknowledgment / backchannel (§4.2) ──────────────────────────────
def test_long_user_message_triggers_acknowledgment():
    assert _plan(user_len=500, since_ack=10).acknowledgment is not None


def test_acknowledgment_disabled_in_task_help():
    assert _plan(mode="task_help", user_len=500, since_ack=10).acknowledgment is None


def test_acknowledgment_respects_frequency_cap():
    assert _plan(user_len=500, since_ack=2).acknowledgment is None  # < 1 per 4 messages


def test_acknowledgment_requires_relationship_stage():
    assert _plan(stage="stranger", user_len=500, since_ack=10).acknowledgment is None


# ── Type 2: Thinking indicator (§4.2) ────────────────────────────────────────
def test_thinking_indicator_on_high_complexity():
    assert _plan(complexity=0.8, mode="deep_reasoning").thinking_indicator is not None


# ── Type 3: Emotional prefix (§4.2) ──────────────────────────────────────────
def test_emotional_prefix_on_sharing_news():
    p = _plan(stage="close_friend", intensity=0.8, turn="sharing_news")
    assert p.emotional_prefix is not None and len(p.emotional_prefix) <= 20


def test_emotional_prefix_requires_friend_stage():
    assert _plan(stage="acquaintance", intensity=0.8, turn="sharing_news").emotional_prefix is None


# ── Type 5: Transition (§4.2) ────────────────────────────────────────────────
def test_transition_mandatory_for_proactive():
    assert _plan(proactive=True).transition_phrase is not None


# ── Type 6: Closing (§4.2) ───────────────────────────────────────────────────
def test_closing_signal_on_farewell():
    assert _plan(stage="close_friend", farewell=True).closing_signal is not None


def test_closing_disabled_in_crisis():
    assert _plan(farewell=True, crisis=True).closing_signal is None


# ── Type 4 + aggregate flags (§4.3) ──────────────────────────────────────────
def test_correction_armed_passes_through():
    assert _plan(correction=True, complexity=0.8).correction_indicator_armed is True


def test_pre_response_signal_flag_and_delay():
    p = _plan(user_len=500, since_ack=10)   # acknowledgment fires
    assert p.any_pre_response_signal is True and p.total_pre_response_delay_ms > 0
