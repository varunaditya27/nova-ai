"""Tests for SC-5 Social Coaching Response Modifier (architecture doc §7)."""

from backend.layer5_relationship import coaching_modifier as cm
from backend.layer5_relationship.schemas import (
    CoachingOpportunity,
    CoachingType,
    DeliveryMode,
    VoiceParameters,
)
from backend.layer4_persona.schemas import FinalResponsePacket


def _response(text="That sounds really tough, and it makes sense you're tired."):
    return FinalResponsePacket(final_text=text, conversation_mode="social_coaching",
                               topic_domain="relationships")


def _opp(delivery=DeliveryMode.INLINE.value, text="One thing I've noticed — you've mentioned this before.",
         coaching_type=CoachingType.PATTERN_REFLECTION.value, person="p1", max_len=120):
    return CoachingOpportunity(opportunity_detected=True, coaching_type=coaching_type,
                               delivery_mode=delivery, observation_text=text,
                               triggering_person=person, max_length_chars=max_len)


def _voice(max_chars=800):
    return VoiceParameters(max_response_length_chars=max_chars)


# ── Pass-through modes (§7.2 Mode 3) ─────────────────────────────────────────
def test_deferred_returns_response_unchanged():
    resp = _response()
    out = cm.inject_observation(resp, _opp(delivery=DeliveryMode.DEFERRED.value), _voice())
    assert out.final_text == resp.final_text
    assert out.social_coaching_injected is False


def test_proactive_future_returns_unchanged():
    resp = _response()
    out = cm.inject_observation(resp, _opp(delivery=DeliveryMode.PROACTIVE_FUTURE.value), _voice())
    assert out.final_text == resp.final_text
    assert out.social_coaching_injected is False


# ── Inline injection (§7.2 Mode 1) ───────────────────────────────────────────
def test_inline_appends_with_transition():
    resp = _response()
    out = cm.inject_observation(resp, _opp(delivery=DeliveryMode.INLINE.value), _voice())
    assert out.social_coaching_injected is True
    assert resp.final_text in out.final_text          # original preserved
    assert "you've mentioned this before" in out.final_text.lower()
    assert len(out.final_text) > len(resp.final_text)


# ── As-question injection (§7.2 Mode 2) ──────────────────────────────────────
def test_as_question_appends_observation():
    resp = _response()
    opp = _opp(delivery=DeliveryMode.AS_QUESTION.value,
               text="Have you noticed that pattern with them?")
    out = cm.inject_observation(resp, opp, _voice())
    assert out.social_coaching_injected is True
    assert out.final_text.rstrip().endswith("Have you noticed that pattern with them?")


# ── Headroom guard (§7.3, §11) ───────────────────────────────────────────────
def test_defers_when_insufficient_headroom():
    resp = _response("x" * 750)
    opp = _opp(max_len=120)
    out = cm.inject_observation(resp, opp, _voice(max_chars=800))   # 50 left < 120 needed
    assert out.final_text == resp.final_text
    assert out.social_coaching_injected is False
    assert opp.delivery_mode == DeliveryMode.DEFERRED.value


# ── Coaching metadata + field preservation (§7.3) ────────────────────────────
def test_injection_sets_metadata_and_preserves_fields():
    resp = _response()
    out = cm.inject_observation(resp, _opp(person="p42"), _voice())
    assert out.coaching_type_injected == CoachingType.PATTERN_REFLECTION.value
    assert out.coaching_person_id == "p42"
    assert out.conversation_mode == "social_coaching"      # preserved from original
    assert out.topic_domain == "relationships"


# ── Transition selection (§7.2) ──────────────────────────────────────────────
def test_select_transition_varies_by_stage():
    close = cm.select_transition("close", CoachingType.PATTERN_REFLECTION.value)
    developing = cm.select_transition("developing", CoachingType.PATTERN_REFLECTION.value)
    assert close != developing
    assert close and developing
