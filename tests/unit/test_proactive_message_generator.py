"""Tests for SC-4 Proactive Message Generator (architecture doc §6)."""

from backend.layer6_proactivity import message_generator as mg
from backend.layer6_proactivity.schemas import (
    ClassifiedInitiative,
    InitiativeType,
    ProactiveContext,
    ProactiveDeliveryPayload,
    ProactiveItem,
    ProactiveItemType,
)


def _classified(max_len=200, initiative=InitiativeType.CURIOUS_FOLLOW_UP.value):
    return ClassifiedInitiative(initiative_type=initiative, max_length_chars=max_len,
                                include_question=True)


def _item(item_type=ProactiveItemType.THREAD_FOLLOW_UP.value):
    return ProactiveItem(item_type=item_type,
                         content_basis="User mentioned a presentation on Tuesday.")


def _context():
    return ProactiveContext(source_memory_summaries=["User had a presentation Tuesday."],
                            persona_instruction="a warm, thoughtful companion",
                            bes_trend_description="has seemed steady lately")


# ── Validation (§6.4) ────────────────────────────────────────────────────────
def test_validate_passes_clean_message():
    res = mg.validate_proactive_message(
        "Hey — how did the presentation end up going?", _classified(), _item())
    assert res.passed is True


def test_validate_fails_over_length():
    res = mg.validate_proactive_message("x" * 250, _classified(max_len=200), _item())
    assert res.passed is False and res.issue == "over_length"


def test_validate_fails_robot_phrase():
    res = mg.validate_proactive_message(
        "Just checking in to see how you are!", _classified(), _item())
    assert res.passed is False and res.action == "regenerate"


def test_validate_fails_too_many_questions():
    res = mg.validate_proactive_message(
        "How are you? Did it go well? What happened next?", _classified(), _item())
    assert res.passed is False and res.issue == "too_many_questions"


def test_validate_fails_assumes_outcome_for_thread():
    res = mg.validate_proactive_message(
        "I'm sure it went well on Tuesday!", _classified(), _item())
    assert res.passed is False and res.issue == "assumes_outcome"


def test_validate_assumption_phrase_ok_for_non_thread_type():
    res = mg.validate_proactive_message(
        "Hope it went great with everything lately.", _classified(),
        _item(ProactiveItemType.WELLBEING_CHECK.value))
    assert res.passed is True


# ── Prompt assembly (§6.3) ───────────────────────────────────────────────────
def test_build_prompt_contains_basis_register_and_length():
    prompt = mg.build_proactive_prompt(_item(), _classified(), _context())
    assert "presentation" in prompt.lower()
    assert "curious_follow_up" in prompt
    assert "200" in prompt


# ── Generation via injected llm_fn (§6.1) ────────────────────────────────────
def test_generate_returns_payload_when_valid():
    def llm(prompt):
        return "Hey — how did the presentation turn out?"

    payload = mg.generate_proactive_message(_item(), _classified(), _context(),
                                            user_id="u1", llm_fn=llm)
    assert isinstance(payload, ProactiveDeliveryPayload)
    assert "presentation" in payload.message_text.lower()
    assert payload.user_id == "u1"
    assert payload.allow_reply is True
    assert payload.tracking_enabled is True


def test_generate_regenerates_after_robot_phrase_then_succeeds():
    outs = iter(["Just checking in!", "Hey — how did Tuesday go?"])

    def llm(prompt):
        return next(outs)

    payload = mg.generate_proactive_message(_item(), _classified(), _context(), llm_fn=llm)
    assert payload is not None
    assert "tuesday" in payload.message_text.lower()


def test_generate_returns_none_after_two_failures():
    def llm(prompt):
        return "Just checking in, wanted to reach out!"   # always robotic

    assert mg.generate_proactive_message(_item(), _classified(), _context(), llm_fn=llm) is None


def test_generate_returns_none_without_llm():
    # §11 hard rule: no pre-written fallback messages — silence over low quality.
    assert mg.generate_proactive_message(_item(), _classified(), _context()) is None
