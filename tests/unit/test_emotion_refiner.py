"""Tests for SC-6 Emotion Refiner / Agent 4b (architecture doc §8)."""

from backend.layer4_persona import emotion_refiner as er
from backend.layer4_persona.schemas import (
    SemanticDraft,
    VoiceParameters,
)
from backend.layer3_reasoning.schemas import BESLabel, EmotionLabel, IntentLabel


# ── Refinement skip policy (§8.2) — all five conditions must hold ────────────
def _skip(**kw):
    base = dict(primary_label=EmotionLabel.NEUTRAL.value,
                bes_label=BESLabel.STABLE_NEUTRAL.value,
                mismatch_detected=False,
                primary_intent=IntentLabel.SEEKING_INFORMATION.value,
                crisis_active=False)
    base.update(kw)
    return er.should_skip_refinement(**base)


def test_skip_when_all_neutral_conditions_true():
    assert _skip() is True


def test_no_skip_when_emotion_present():
    assert _skip(primary_label=EmotionLabel.ANXIETY.value) is False


def test_no_skip_when_negative_drift():
    assert _skip(bes_label=BESLabel.DETERIORATING.value) is False


def test_no_skip_when_mismatch_detected():
    assert _skip(mismatch_detected=True) is False


def test_no_skip_when_crisis_active():
    assert _skip(crisis_active=True) is False


def test_no_skip_when_intent_not_neutral():
    assert _skip(primary_intent=IntentLabel.VENTING.value) is False


# ── Factual-preservation validation (§8.6) ───────────────────────────────────
def test_validate_passes_when_claims_present():
    refined = "I know the exam is on Friday, and you can retake it next semester."
    res = er.validate_factual_preservation(
        refined, ["The exam is on Friday.", "You can retake it next semester."])
    assert res.passed is True
    assert res.missing_claims == []


def test_validate_flags_missing_claim():
    refined = "I hear how hard this is right now."
    res = er.validate_factual_preservation(refined, ["The deadline was extended to Monday."])
    assert res.passed is False
    assert "The deadline was extended to Monday." in res.missing_claims
    assert res.action == "reinsert"


def test_reinsert_appends_missing_claim():
    out = er.reinsert_claims("I hear you.", ["The deadline was extended to Monday."])
    assert "deadline was extended to monday" in out.lower()


# ── Full refinement (§8.1, §8.5) ─────────────────────────────────────────────
def test_refine_skip_passes_draft_through_unchanged():
    draft = SemanticDraft(text="The library opens at nine.")
    out = er.refine_emotion(draft, skip=True)
    assert out.final_text == "The library opens at nine."
    assert out.refinement_applied is False
    assert out.refinement_skipped_reason


def test_refine_without_llm_falls_back_to_draft():
    # §12: no refiner available → pass the semantic draft through unchanged.
    draft = SemanticDraft(text="The report is due Friday.",
                          key_claims=["The report is due Friday."])
    out = er.refine_emotion(draft, skip=False)
    assert out.final_text == "The report is due Friday."
    assert out.refinement_applied is False


def test_refine_uses_llm_and_preserves_facts():
    draft = SemanticDraft(text="You can retake the exam next semester.",
                          key_claims=["You can retake the exam next semester."])

    def fake_refiner(prompt):
        return ("I'm really sorry this happened — that's a heavy thing to sit with. "
                "When you're ready, you can retake the exam next semester.")

    out = er.refine_emotion(draft, skip=False, llm_fn=fake_refiner)
    assert out.refinement_applied is True
    assert out.factual_validation_passed is True
    assert "retake the exam next semester" in out.final_text.lower()


def test_refine_reinserts_dropped_claim():
    draft = SemanticDraft(text="Your appointment is on Tuesday at 3pm.",
                          key_claims=["Your appointment is on Tuesday at 3pm."])

    def dropping_refiner(prompt):
        return "I know things feel overwhelming right now, and that's completely understandable."

    out = er.refine_emotion(draft, skip=False, llm_fn=dropping_refiner)
    assert "tuesday at 3pm" in out.final_text.lower()       # reinserted
    assert "Your appointment is on Tuesday at 3pm." in out.factual_claims_reinserted


def test_refine_falls_back_to_draft_on_llm_error():
    draft = SemanticDraft(text="The deadline is Monday.", key_claims=["The deadline is Monday."])

    def exploding_refiner(prompt):
        raise RuntimeError("refiner down")

    out = er.refine_emotion(draft, skip=False, llm_fn=exploding_refiner)
    assert out.final_text == "The deadline is Monday."
    assert out.refinement_applied is False


# ── Prompt assembly (§8.5) ───────────────────────────────────────────────────
def test_build_refiner_prompt_contains_claims_and_posture():
    draft = SemanticDraft(text="You can retake it.", key_claims=["You can retake it next semester."])
    prompt = er.build_refiner_prompt(
        semantic_draft=draft, voice_parameters=VoiceParameters(validation_first=True),
        emotional_posture_instruction="Validate first, then gently inform.")
    assert "You can retake it next semester." in prompt
    assert "Validate first, then gently inform." in prompt
    assert "do not" in prompt.lower()       # preservation instruction present
