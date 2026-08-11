"""SC-3 VoiceParameters (architecture doc §5)."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import (
    ContractionPolicy,
    HumorMode,
    HumorType,
    ParagraphDensity,
    QuestionType,
    Register,
    SelfDisclosureDepth,
    SentenceLength,
    TargetResponseLength,
    VocabularyTier,
)


@dataclass
class VoiceParameters:
    """Precise, deterministic style directives for the two planners (§5.2)."""

    # Register
    register: str = Register.NATURAL.value
    register_note: str = ""

    # Sentence structure
    sentence_length: str = SentenceLength.MEDIUM.value
    paragraph_density: str = ParagraphDensity.NORMAL.value
    use_lists: bool = False
    use_markdown: bool = False

    # Lexical
    vocabulary_tier: str = VocabularyTier.STANDARD.value
    contraction_policy: str = ContractionPolicy.PREFERRED.value
    filler_expression_allowed: bool = False

    # Emotional expression
    warmth_expression: float = 0.6
    empathy_explicitness: float = 0.3
    validation_first: bool = False
    celebration_energy: float = 0.0

    # Humor
    humor_mode: str = HumorMode.NONE.value
    humor_type: str = HumorType.DRY.value

    # Length
    target_response_length: str = TargetResponseLength.SHORT.value
    max_response_length_chars: int = 500

    # Epistemic stance
    hedging_level: float = 0.1
    certainty_phrase_allowed: bool = True
    opinion_expression_allowed: bool = True

    # Follow-up question policy
    follow_up_question_allowed: bool = True
    follow_up_question_max: int = 1
    question_type: str = QuestionType.OPEN.value

    # Self-disclosure
    self_disclosure_allowed: bool = False
    self_disclosure_depth: str = SelfDisclosureDepth.NONE.value
