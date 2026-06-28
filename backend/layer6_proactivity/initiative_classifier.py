"""SC-2 — Initiative Classifier (architecture doc §4).

Takes a candidate item from SC-1 and determines its initiative type, content framing,
and emotional register for delivery. Fully deterministic — classification rules over the
item's type and context metadata. No LLM call. The output ``ClassifiedInitiative`` is the
generation blueprint SC-4 consumes directly.
"""

from __future__ import annotations

from backend.layer6_proactivity.schemas import (
    ClassifiedInitiative,
    ContentFraming,
    EmotionalRegister,
    InitiativeType,
    ProactiveItem,
    ProactiveItemType,
    QuestionType,
    ReferenceDepth,
    Urgency,
)

_LONG_SILENCE_DAYS = 21
_POSITIVE_ANTICIPATION = 0.3
_DETERIORATING_TRENDS = {"significant_negative_drift", "deteriorating"}

_GENTLE_NUDGE_TYPES = {
    ProactiveItemType.GOAL_CHECK_IN.value,
    ProactiveItemType.GOAL_ENCOURAGEMENT.value,
    ProactiveItemType.SOCIAL_PATTERN_COACHING.value,
    ProactiveItemType.RELATIONSHIP_CHECK_IN.value,
}
_THREAD_TYPES = {
    ProactiveItemType.THREAD_FOLLOW_UP.value,
    ProactiveItemType.UPCOMING_DATE_REMINDER.value,
}

# Per-initiative delivery parameters (architecture doc §4.4).
_DELIVERY_PARAMS: dict[str, tuple[int, bool, str]] = {
    InitiativeType.RECONNECTION_OPENER.value: (160, True, QuestionType.OPEN.value),
    InitiativeType.CONCERNED_CHECK_IN.value: (220, True, QuestionType.CHECKING_IN.value),
    InitiativeType.CARING_CHECK_IN.value: (180, True, QuestionType.OPEN.value),
    InitiativeType.CELEBRATORY_FOLLOW_UP.value: (200, True, QuestionType.SPECIFIC.value),
    InitiativeType.CURIOUS_FOLLOW_UP.value: (200, True, QuestionType.SPECIFIC.value),
    InitiativeType.GENTLE_NUDGE.value: (200, True, QuestionType.OPEN.value),
    InitiativeType.ANNIVERSARY_RECALL.value: (200, False, QuestionType.NONE.value),
}


def _finalize(ci: ClassifiedInitiative) -> ClassifiedInitiative:
    length, include_q, q_type = _DELIVERY_PARAMS.get(
        ci.initiative_type, (200, True, QuestionType.OPEN.value)
    )
    ci.max_length_chars = length
    ci.include_question = include_q
    ci.question_type = q_type
    return ci


def classify_initiative(
    item: ProactiveItem,
    bes_trend: str,
    relationship_stage: str,
    session_gap_days: int,
) -> ClassifiedInitiative:
    """Classify a candidate item into a delivery blueprint (architecture doc §4.3)."""
    # Long silence → careful reconnection (overrides type-specific branches).
    if session_gap_days >= _LONG_SILENCE_DAYS:
        return _finalize(ClassifiedInitiative(
            initiative_type=InitiativeType.RECONNECTION_OPENER.value,
            emotional_register=EmotionalRegister.WARM_CAREFUL.value,
            content_framing=ContentFraming.OPEN_ENDED.value,
            reference_depth=ReferenceDepth.MINIMAL.value,
            urgency=Urgency.LOW.value,
            opening_posture="gentle_reconnect",
        ))

    # Emotional check-in: concerned vs caring, by BES trend.
    if item.item_type == ProactiveItemType.EMOTIONAL_CHECK_IN.value:
        if bes_trend in _DETERIORATING_TRENDS:
            return _finalize(ClassifiedInitiative(
                initiative_type=InitiativeType.CONCERNED_CHECK_IN.value,
                emotional_register=EmotionalRegister.WARM_DIRECT.value,
                content_framing=ContentFraming.FEELING_FOCUSED.value,
                reference_depth=ReferenceDepth.SPECIFIC.value,
                urgency=Urgency.MEDIUM.value,
                opening_posture="emotional_presence",
            ))
        return _finalize(ClassifiedInitiative(
            initiative_type=InitiativeType.CARING_CHECK_IN.value,
            emotional_register=EmotionalRegister.WARM_CASUAL.value,
            content_framing=ContentFraming.LIGHT_TOUCH.value,
            reference_depth=ReferenceDepth.VAGUE.value,
            urgency=Urgency.LOW.value,
            opening_posture="soft_check",
        ))

    # Thread / upcoming date: celebratory vs curious, by anticipation valence.
    if item.item_type in _THREAD_TYPES:
        valence = item.content_basis_valence or 0.0
        if valence > _POSITIVE_ANTICIPATION:
            return _finalize(ClassifiedInitiative(
                initiative_type=InitiativeType.CELEBRATORY_FOLLOW_UP.value,
                emotional_register=EmotionalRegister.WARM_ENERGETIC.value,
                content_framing=ContentFraming.EVENT_SPECIFIC.value,
                reference_depth=ReferenceDepth.SPECIFIC.value,
                urgency=Urgency.MEDIUM.value,
                opening_posture="celebration_ready",
            ))
        return _finalize(ClassifiedInitiative(
            initiative_type=InitiativeType.CURIOUS_FOLLOW_UP.value,
            emotional_register=EmotionalRegister.WARM_NEUTRAL.value,
            content_framing=ContentFraming.EVENT_SPECIFIC.value,
            reference_depth=ReferenceDepth.SPECIFIC.value,
            urgency=Urgency.MEDIUM.value,
            opening_posture="open_curiosity",
        ))

    # Goal / social coaching → gentle nudge.
    if item.item_type in _GENTLE_NUDGE_TYPES:
        return _finalize(ClassifiedInitiative(
            initiative_type=InitiativeType.GENTLE_NUDGE.value,
            emotional_register=EmotionalRegister.WARM_LIGHT.value,
            content_framing=ContentFraming.INVITATIONAL.value,
            reference_depth=ReferenceDepth.VAGUE.value,
            urgency=Urgency.LOW.value,
            opening_posture="low_pressure",
        ))

    # Default: caring check-in.
    return _finalize(ClassifiedInitiative(
        initiative_type=InitiativeType.CARING_CHECK_IN.value,
        emotional_register=EmotionalRegister.WARM_CASUAL.value,
        content_framing=ContentFraming.OPEN_ENDED.value,
        reference_depth=ReferenceDepth.VAGUE.value,
        urgency=Urgency.LOW.value,
        opening_posture="soft_check",
    ))
