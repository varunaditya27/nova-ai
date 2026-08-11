"""SC-2 ClassifiedInitiative (architecture doc §4)."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import ContentFraming, EmotionalRegister, InitiativeType, QuestionType, ReferenceDepth, Urgency


@dataclass
class ClassifiedInitiative:
    initiative_type: str = InitiativeType.CARING_CHECK_IN.value
    emotional_register: str = EmotionalRegister.WARM_CASUAL.value
    content_framing: str = ContentFraming.OPEN_ENDED.value
    reference_depth: str = ReferenceDepth.VAGUE.value
    urgency: str = Urgency.LOW.value
    opening_posture: str = "soft_check"
    max_length_chars: int = 200
    include_question: bool = True
    question_type: str = QuestionType.OPEN.value
