"""SC-5 — Empathy Hypothesis Generator (architecture doc §7).

The Empathy Hypothesis is the auditable bridge between classification and generation: an
explicit, structured statement of what the user is feeling, what they need, the response
posture, and what to withhold. Making this reasoning explicit (rather than implicit in the
LLM's next-token generation) is what makes Nova's emotional logic testable and correctable.

Generation is deterministic rule synthesis over the SC-1..SC-4 outputs — no LLM call.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer3_reasoning.schemas import (
    BackgroundEmotionalState,
    BESLabel,
    DisclosureDepth,
    EmotionClassification,
    EmotionLabel,
    EmpathyHypothesis,
    IntentClassification,
    IntentLabel,
    MismatchResult,
    PrimaryNeed,
    ResponsePosture,
)

# Intent → default need (architecture doc §7.3 step 1).
_INTENT_NEED = {
    IntentLabel.VENTING.value: PrimaryNeed.TO_BE_HEARD.value,
    IntentLabel.SEEKING_VALIDATION.value: PrimaryNeed.TO_BE_VALIDATED.value,
    IntentLabel.SEEKING_COMFORT.value: PrimaryNeed.TO_BE_HEARD.value,
    IntentLabel.SHARING_GOOD_NEWS.value: PrimaryNeed.TO_CELEBRATE.value,
    IntentLabel.CASUAL_CHAT.value: PrimaryNeed.DISTRACTION.value,
    IntentLabel.CHECK_IN.value: PrimaryNeed.TO_BE_HEARD.value,
    IntentLabel.SEEKING_ADVICE.value: PrimaryNeed.TO_PROBLEM_SOLVE.value,
    IntentLabel.SEEKING_INFORMATION.value: PrimaryNeed.INFORMATION.value,
    IntentLabel.THINKING_ALOUD.value: PrimaryNeed.TO_THINK_ALOUD.value,
    IntentLabel.PROBLEM_SOLVING.value: PrimaryNeed.TO_PROBLEM_SOLVE.value,
    IntentLabel.GOAL_SETTING.value: PrimaryNeed.TO_PROBLEM_SOLVE.value,
    IntentLabel.DECISION_SUPPORT.value: PrimaryNeed.TO_DECIDE.value,
    IntentLabel.PROVIDING_UPDATE.value: PrimaryNeed.TO_BE_HEARD.value,
    IntentLabel.EXPRESSING_GRATITUDE.value: PrimaryNeed.TO_BE_HEARD.value,
    IntentLabel.EXPRESSING_COMPLAINT.value: PrimaryNeed.TO_BE_HEARD.value,
    IntentLabel.TESTING_NOVA.value: PrimaryNeed.INFORMATION.value,
    IntentLabel.REQUESTING_REFLECTION.value: PrimaryNeed.TO_THINK_ALOUD.value,
}

# Low-arousal negative emotions where the user is processing — give space, don't fill it.
_SIT_WITH_IT_EMOTIONS = {
    EmotionLabel.SADNESS.value, EmotionLabel.NUMBNESS.value, EmotionLabel.DESPAIR.value,
}

# Need → (default posture, BES-negative-drift override posture) (architecture doc §7.4).
_NEED_POSTURE = {
    PrimaryNeed.TO_BE_HEARD.value: (ResponsePosture.VALIDATE_THEN_HOLD.value,
                                    ResponsePosture.VALIDATE_THEN_HOLD.value),
    PrimaryNeed.TO_BE_VALIDATED.value: (ResponsePosture.VALIDATE_THEN_HOLD.value,
                                        ResponsePosture.VALIDATE_THEN_HOLD.value),
    PrimaryNeed.TO_CELEBRATE.value: (ResponsePosture.CELEBRATE.value,
                                     ResponsePosture.CELEBRATE.value),
    PrimaryNeed.TO_PROBLEM_SOLVE.value: (ResponsePosture.VALIDATE_THEN_SOLVE.value,
                                         ResponsePosture.VALIDATE_THEN_SOLVE.value),
    PrimaryNeed.TO_THINK_ALOUD.value: (ResponsePosture.CO_THINK.value,
                                       ResponsePosture.CO_THINK.value),
    PrimaryNeed.TO_DECIDE.value: (ResponsePosture.CO_THINK.value,
                                  ResponsePosture.VALIDATE_THEN_SOLVE.value),
    PrimaryNeed.SPACE_TO_SIT_WITH_IT.value: (ResponsePosture.LISTEN_ONLY.value,
                                             ResponsePosture.LISTEN_ONLY.value),
    PrimaryNeed.INFORMATION.value: (ResponsePosture.INFORM_WITH_WARMTH.value,
                                    ResponsePosture.INFORM_WITH_WARMTH.value),
    PrimaryNeed.DISTRACTION.value: (ResponsePosture.INFORM_WITH_WARMTH.value,
                                    ResponsePosture.GENTLE_REDIRECT.value),
    PrimaryNeed.CRISIS_SUPPORT.value: (ResponsePosture.CRISIS_PROTOCOL.value,
                                       ResponsePosture.CRISIS_PROTOCOL.value),
}

_NEGATIVE_DRIFT = {
    BESLabel.MILD_NEGATIVE_DRIFT.value,
    BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value,
    BESLabel.DETERIORATING.value,
}

_ADVICE_WITHHELD_NEEDS = {
    PrimaryNeed.TO_BE_HEARD.value,
    PrimaryNeed.TO_BE_VALIDATED.value,
    PrimaryNeed.SPACE_TO_SIT_WITH_IT.value,
}
_ADVICE_WITHHELD_POSTURES = {
    ResponsePosture.VALIDATE_THEN_HOLD.value,
    ResponsePosture.LISTEN_ONLY.value,
}


def map_intent_emotion_to_need(primary_intent: str, primary_emotion: EmotionClassification) -> str:
    """Resolve the user's primary need from intent + emotion (architecture doc §7.3)."""
    need = _INTENT_NEED.get(primary_intent, PrimaryNeed.INFORMATION.value)
    # A user venting in low-arousal grief needs space more than active acknowledgment.
    if (need == PrimaryNeed.TO_BE_HEARD.value
            and primary_emotion.primary_label in _SIT_WITH_IT_EMOTIONS
            and primary_emotion.arousal < 0.3):
        need = PrimaryNeed.SPACE_TO_SIT_WITH_IT.value
    return need


def map_need_to_posture(need: str, bes_label: str, relationship_depth: float) -> str:
    """Map need → posture, applying the BES negative-drift override (architecture doc §7.4)."""
    default_posture, drift_posture = _NEED_POSTURE.get(
        need, (ResponsePosture.INFORM_WITH_WARMTH.value, ResponsePosture.INFORM_WITH_WARMTH.value))
    return drift_posture if bes_label in _NEGATIVE_DRIFT else default_posture


def _describe_feeling(emotion: EmotionClassification, bes: BackgroundEmotionalState) -> str:
    label = emotion.primary_label
    if bes.bes_label in _NEGATIVE_DRIFT:
        return f"{label}, against a background of {bes.bes_label.replace('_', ' ')}"
    return label


def _construct_basis(emotion, bes, mismatch) -> str:
    parts = [f"primary emotion {emotion.primary_label} (valence {emotion.valence:+.2f})"]
    if bes.bes_label not in (BESLabel.STABLE_NEUTRAL.value, BESLabel.INSUFFICIENT_DATA.value):
        parts.append(f"background state {bes.bes_label}")
    if mismatch.mismatch_detected:
        parts.append(f"stated-vs-felt mismatch ({mismatch.mismatch_type})")
    return "; ".join(parts)


def generate_empathy_hypothesis(
    primary_emotion: EmotionClassification,
    background_state: BackgroundEmotionalState,
    intent: IntentClassification,
    mismatch: MismatchResult,
    relationship_depth: float = 0.0,
    uwm_psychological=None,
) -> EmpathyHypothesis:
    """Synthesise the auditable empathy hypothesis (architecture doc §7.3)."""
    # 1. Base need from intent + emotion.
    need = map_intent_emotion_to_need(intent.primary_intent, primary_emotion)

    # 2. A confident mismatch trumps stated intent — lead with presence.
    if mismatch.mismatch_detected and mismatch.mismatch_confidence > 0.6:
        if need != PrimaryNeed.CRISIS_SUPPORT.value:
            need = PrimaryNeed.TO_BE_HEARD.value

    # 3. Crisis overrides everything.
    if primary_emotion.crisis_flag:
        need = PrimaryNeed.CRISIS_SUPPORT.value

    # 4. Need → posture (with BES override).
    posture = map_need_to_posture(need, background_state.bes_label, relationship_depth)

    # 5. Honour a known solution-oriented support preference.
    if (uwm_psychological is not None
            and getattr(uwm_psychological, "preferred_support_style", None) == "solution_oriented"
            and posture == ResponsePosture.VALIDATE_THEN_HOLD.value):
        posture = ResponsePosture.VALIDATE_THEN_SOLVE.value

    # 6. Disclosure depth from relationship depth.
    if relationship_depth < 0.25:
        disclosure = DisclosureDepth.SURFACE.value
    elif relationship_depth < 0.60:
        disclosure = DisclosureDepth.MODERATE.value
    else:
        disclosure = DisclosureDepth.DEEP.value

    # 7. Advice policy.
    advice_withheld = (
        intent.prefers_no_advice
        or need in _ADVICE_WITHHELD_NEEDS
        or posture in _ADVICE_WITHHELD_POSTURES
    )

    skip_refinement = (
        primary_emotion.primary_label == EmotionLabel.NEUTRAL.value
        and background_state.bes_label not in _NEGATIVE_DRIFT
        and not mismatch.mismatch_detected
    )

    return EmpathyHypothesis(
        primary_feeling=_describe_feeling(primary_emotion, background_state),
        feeling_basis=_construct_basis(primary_emotion, background_state, mismatch),
        primary_need=need,
        response_posture=posture,
        advice_withheld=advice_withheld,
        advice_withheld_reason=(
            "user preference or emotional state" if advice_withheld else None),
        apply_mismatch_posture=mismatch.mismatch_detected,
        mismatch_posture=mismatch.mismatch_response_posture if mismatch.mismatch_detected else None,
        disclosure_depth_allowed=disclosure,
        is_crisis=primary_emotion.crisis_flag,
        skip_emotional_refinement=skip_refinement,
        generated_at=datetime.utcnow(),
        basis_summary=(
            f"User needs {need.replace('_', ' ')}; posture {posture.replace('_', ' ')}."),
    )
