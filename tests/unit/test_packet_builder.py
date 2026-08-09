"""Tests for the Layer 3 orchestrator / EmotionIntentPacket builder (architecture doc §9, §12)."""

from backend.layer3_reasoning import packet_builder as pb
from backend.layer3_reasoning.schemas import (
    AdviceGate,
    ConversationMode,
    EmpathyHypothesis,
    EmotionIntentPacket,
    LLMClassificationOutput,
    MismatchResult,
    ResponsePacing,
    ResponsePosture,
)


# ── Response instruction construction (§9.1) ─────────────────────────────────
def test_validate_then_hold_instruction_forbids_solutions():
    base, posture = pb.construct_response_instruction(
        EmpathyHypothesis(response_posture=ResponsePosture.VALIDATE_THEN_HOLD.value),
        ConversationMode.EMOTIONAL_SUPPORT.value,
        MismatchResult(mismatch_detected=False))
    assert "unless they explicitly ask" in base.lower() or "do not offer" in base.lower()
    assert posture  # non-empty posture instruction


def test_mismatch_adds_gentle_opening_addendum():
    base_no, _ = pb.construct_response_instruction(
        EmpathyHypothesis(response_posture=ResponsePosture.VALIDATE_THEN_HOLD.value,
                          apply_mismatch_posture=False),
        ConversationMode.EMOTIONAL_SUPPORT.value, MismatchResult(mismatch_detected=False))
    base_yes, _ = pb.construct_response_instruction(
        EmpathyHypothesis(response_posture=ResponsePosture.VALIDATE_THEN_HOLD.value,
                          apply_mismatch_posture=True),
        ConversationMode.EMOTIONAL_SUPPORT.value, MismatchResult(mismatch_detected=True))
    assert len(base_yes) > len(base_no)
    assert "opening" in base_yes.lower()


# ── Advice gate (§9) ─────────────────────────────────────────────────────────
def test_advice_gate_closed_when_withheld():
    gate = pb.construct_advice_gate(
        EmpathyHypothesis(advice_withheld=True), prefers_no_advice=True)
    assert gate == AdviceGate.CLOSED.value


def test_advice_gate_open_for_solve_posture():
    gate = pb.construct_advice_gate(
        EmpathyHypothesis(response_posture=ResponsePosture.VALIDATE_THEN_SOLVE.value,
                          advice_withheld=False), prefers_no_advice=False)
    assert gate == AdviceGate.OPEN.value


def test_advice_gate_gated_by_default():
    gate = pb.construct_advice_gate(
        EmpathyHypothesis(response_posture=ResponsePosture.CO_THINK.value,
                          advice_withheld=False), prefers_no_advice=False)
    assert gate == AdviceGate.GATED.value


# ── Pacing (§8.3, §9) ────────────────────────────────────────────────────────
def test_pacing_crisis_is_immediate():
    pacing, pause = pb.pacing_for_mode(ConversationMode.CRISIS.value)
    assert pacing == ResponsePacing.IMMEDIATE.value
    assert pause == 0


def test_pacing_emotional_support_is_slow():
    pacing, _ = pb.pacing_for_mode(ConversationMode.EMOTIONAL_SUPPORT.value)
    assert pacing == ResponsePacing.SLOW.value


def test_pacing_life_review_is_contemplative():
    pacing, pause = pb.pacing_for_mode(ConversationMode.LIFE_REVIEW.value)
    assert pacing == ResponsePacing.CONTEMPLATIVE.value
    assert pause > 0


# ── Full packet build (§9) ───────────────────────────────────────────────────
def test_build_packet_neutral_informational_no_llm():
    packet = pb.build_emotion_intent_packet(
        "the report is due friday", implicit_intensity=0.05, circadian_band="afternoon")
    assert isinstance(packet, EmotionIntentPacket)
    assert packet.conversation_mode == ConversationMode.CASUAL.value
    assert packet.crisis_active is False
    assert packet.llm_call_made is False


def test_build_packet_uses_llm_for_ambiguous():
    def fake_llm(msg):
        return LLMClassificationOutput(
            primary_label="anxiety", valence=-0.5, arousal=0.7, confidence=0.8,
            primary_intent="venting", intent_confidence=0.7)

    packet = pb.build_emotion_intent_packet(
        "I really can't handle how everything is going right now",
        implicit_intensity=0.6, circadian_band="late_night",
        composite_prior=0.7, prior_confidence=0.8, llm_fn=fake_llm)
    assert packet.llm_call_made is True
    assert packet.conversation_mode == ConversationMode.EMOTIONAL_SUPPORT.value
    assert 0.0 <= packet.classification_confidence_overall <= 1.0


def test_build_packet_crisis_emits_alert_before_completion():
    alerts = []

    packet = pb.build_emotion_intent_packet(
        "I just want to die, I can't go on", implicit_intensity=0.9,
        circadian_band="late_night", alert_fn=alerts.append)
    assert packet.crisis_active is True
    assert packet.conversation_mode == ConversationMode.CRISIS.value
    assert packet.crisis_confidence > 0.65
    assert len(alerts) == 1                       # alert emitted to L8/L11
    assert alerts[0].crisis_confidence > 0.65


def test_build_packet_crisis_alert_fires_even_without_llm_or_failure():
    # §12 hard rule: crisis alert always emitted regardless of other failures.
    def exploding_llm(msg):
        raise RuntimeError("model down")

    alerts = []
    packet = pb.build_emotion_intent_packet(
        "I want to kill myself", implicit_intensity=0.95, circadian_band="late_night",
        llm_fn=exploding_llm, alert_fn=alerts.append)
    assert len(alerts) == 1
    assert packet.crisis_active is True


def test_build_packet_never_raises_on_bad_inputs():
    # Degraded path: garbage everything still yields a valid packet (§12 hard rule).
    packet = pb.build_emotion_intent_packet("", implicit_intensity=0.0)
    assert isinstance(packet, EmotionIntentPacket)
    assert packet.conversation_mode in {m.value for m in ConversationMode}


# ── Shared SC-1/SC-3 LLM call (architecture doc §14.2) ───────────────────────
def _counting_llm(calls, **overrides):
    def fn(msg):
        calls.append(msg)
        kwargs = dict(primary_label="anxiety", valence=-0.5, arousal=0.7, confidence=0.8,
                     primary_intent="venting", intent_confidence=0.7)
        kwargs.update(overrides)
        return LLMClassificationOutput(**kwargs)
    return fn


def test_shared_call_fires_once_when_both_halves_are_ambiguous():
    calls = []
    packet = pb.build_emotion_intent_packet(
        "I really can't handle how everything is going right now",
        implicit_intensity=0.6, circadian_band="late_night",
        composite_prior=0.7, prior_confidence=0.8, llm_fn=_counting_llm(calls))
    assert len(calls) == 1
    assert packet.llm_call_made is True
    assert packet.intent.primary_intent == "venting"


def test_shared_call_fires_once_when_only_emotion_is_ambiguous():
    # "just need to vent" resolves intent by rule (VENTING, high confidence) -- only emotion
    # needs the LLM. The shared call must still fire exactly once, not be skipped.
    calls = []
    pb.build_emotion_intent_packet(
        "just need to vent, everything feels like too much today", implicit_intensity=0.5,
        llm_fn=_counting_llm(calls))
    assert len(calls) == 1


def test_shared_call_fires_once_when_only_intent_is_ambiguous():
    # A short, punctuation-free, low-intensity message resolves emotion heuristically to neutral
    # (skips the LLM there) but has no confident intent rule match -- only intent needs the LLM.
    calls = []
    pb.build_emotion_intent_packet(
        "not sure what to make of this", implicit_intensity=0.05, circadian_band="afternoon",
        llm_fn=_counting_llm(calls))
    assert len(calls) == 1


def test_shared_call_never_fires_when_neither_half_is_ambiguous():
    # Heuristic-neutral emotion + a confident rule-matched intent: no LLM call at all.
    calls = []
    packet = pb.build_emotion_intent_packet(
        "just want to vent", implicit_intensity=0.05, circadian_band="afternoon",
        llm_fn=_counting_llm(calls))
    assert len(calls) == 0
    assert packet.llm_call_made is False


def test_shared_call_crisis_flag_from_llm_reaches_the_packet():
    # The LLM half of the shared call can itself surface a crisis the heuristic prefilter
    # missed -- must still propagate through the merged path to the packet and the alert.
    calls = []
    llm = _counting_llm(calls, primary_label="despair", valence=-0.9, arousal=0.3,
                        confidence=0.9, crisis_flag=True, crisis_confidence=0.88,
                        primary_intent="venting", intent_confidence=0.6)
    alerts = []
    packet = pb.build_emotion_intent_packet(
        "everything feels pointless lately", implicit_intensity=0.7, circadian_band="late_night",
        llm_fn=llm, alert_fn=alerts.append)
    assert len(calls) == 1
    assert packet.crisis_active is True
    assert packet.crisis_confidence == 0.88
    assert packet.conversation_mode == ConversationMode.CRISIS.value
    assert len(alerts) == 1 and alerts[0].source == "layer3_llm"


def test_shared_call_heuristic_crisis_still_wins_over_a_calmer_shared_llm_read():
    # §3.6 hard rule, now exercised through the merged call path: a heuristic crisis keyword
    # must not be overridden even if the single shared LLM response reads calm.
    calls = []
    calm_llm = _counting_llm(calls, primary_label="neutral", valence=0.1, arousal=0.2,
                             confidence=0.6, crisis_flag=False, crisis_confidence=0.0,
                             primary_intent="casual_chat", intent_confidence=0.5)
    packet = pb.build_emotion_intent_packet(
        "I want to kill myself", implicit_intensity=0.95, circadian_band="late_night",
        llm_fn=calm_llm)
    assert len(calls) == 1
    assert packet.crisis_active is True
    assert packet.conversation_mode == ConversationMode.CRISIS.value


def test_build_packet_populates_instructions_and_gate():
    packet = pb.build_emotion_intent_packet(
        "the meeting moved to 3pm", implicit_intensity=0.05, circadian_band="afternoon")
    assert packet.response_instruction
    assert packet.emotional_posture_instruction
    assert packet.advice_gate in {g.value for g in AdviceGate}
    assert packet.suggested_response_pacing in {p.value for p in ResponsePacing}
