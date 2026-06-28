"""Tests for SC-5 Semantic Planner / Agent 4a (architecture doc §7)."""

from backend.layer4_persona import semantic_planner as sp
from backend.layer4_persona.schemas import (
    AdviceGate,
    PersonaPacket,
    SemanticDraft,
)


# ── Key-claim extraction (§7.5) ──────────────────────────────────────────────
def test_extract_key_claims_skips_questions():
    text = "The exam is on Friday. You can retake it next semester. How are you holding up?"
    claims = sp.extract_key_claims(text)
    assert any("exam is on friday" in c.lower() for c in claims)
    assert all("how are you holding up" not in c.lower() for c in claims)


# ── Advice detection (§7.6) ──────────────────────────────────────────────────
def test_detect_advice_true_on_recommendation():
    assert sp.detect_advice("You should talk to her about it.") is True
    assert sp.detect_advice("Have you considered emailing the professor?") is True


def test_detect_advice_false_on_plain_statement():
    assert sp.detect_advice("The deadline is Friday at noon.") is False


# ── Advice-gate validation (§7.6) ────────────────────────────────────────────
def test_advice_gate_closed_flags_advice():
    draft = SemanticDraft(text="You should email them.", advice_included=True)
    res = sp.validate_advice_gate(draft, AdviceGate.CLOSED.value)
    assert res.passed is False
    assert res.action == "strip_advice"


def test_advice_gate_open_passes_with_advice():
    draft = SemanticDraft(text="You should email them.", advice_included=True)
    res = sp.validate_advice_gate(draft, AdviceGate.OPEN.value)
    assert res.passed is True


def test_advice_gate_gated_strips_when_not_explicitly_asked():
    draft = SemanticDraft(text="You should email them.", advice_included=True)
    not_asked = sp.validate_advice_gate(draft, AdviceGate.GATED.value, explicitly_asked=False)
    asked = sp.validate_advice_gate(draft, AdviceGate.GATED.value, explicitly_asked=True)
    assert not_asked.passed is False
    assert asked.passed is True


# ── Advice stripping (§7.6 — no LLM call) ────────────────────────────────────
def test_strip_advice_removes_advice_sentences():
    text = "The deadline is Friday. You should email the professor today."
    stripped = sp.strip_advice(text)
    assert "deadline is friday" in stripped.lower()
    assert "should email" not in stripped.lower()


# ── Draft generation via injected llm_fn (§7.2) ──────────────────────────────
def test_generate_draft_uses_llm_fn():
    def fake_llm(prompt):
        return "The library opens at nine on weekdays."

    draft = sp.generate_semantic_draft("when does the library open?", llm_fn=fake_llm)
    assert isinstance(draft, SemanticDraft)
    assert "library opens at nine" in draft.text.lower()
    assert draft.word_count == 7
    assert 0.0 <= draft.complexity_score <= 1.0


def test_generate_draft_closed_gate_strips_advice():
    def fake_llm(prompt):
        return "Your results are valid. You should definitely retake the test."

    draft = sp.generate_semantic_draft(
        "I failed", advice_gate=AdviceGate.CLOSED.value, llm_fn=fake_llm)
    assert draft.advice_included is False
    assert "should definitely retake" not in draft.text.lower()
    assert "results are valid" in draft.text.lower()


def test_generate_draft_fallback_without_llm_is_non_empty():
    # §12: malformed/absent planner output still yields a usable, non-empty draft.
    draft = sp.generate_semantic_draft("hello there")
    assert draft.text                      # non-empty
    assert draft.advice_included is False


# ── Prompt assembly (§7.4) ───────────────────────────────────────────────────
def test_build_planner_prompt_includes_constraints_gate_and_message():
    packet = PersonaPacket(persona_instruction="You are Nova, a warm companion.",
                           constraint_instruction="Do not fabricate emotions.")
    prompt = sp.build_planner_prompt(
        user_message="what time is it?", persona_packet=packet,
        advice_gate=AdviceGate.GATED.value, response_instruction="Answer plainly.")
    assert "what time is it?" in prompt
    assert "gated" in prompt
    assert "warm companion" in prompt
    assert "Do not fabricate emotions." in prompt
