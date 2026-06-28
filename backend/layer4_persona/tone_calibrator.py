"""SC-3 — Tone & Style Calibrator (architecture doc §5).

Takes the PersonaState, RelationshipState, and the upstream emotional context and
produces a ``VoiceParameters`` struct — the precise, plain-language style directives
injected into the Semantic Planner and Emotion Refiner prompts.

Fully deterministic; no LLM call (target < 2ms). This is the layer that translates
numbers into language (design principle §14.4): valence/arousal floats never reach
the LLM — they have already been turned into a conversation mode and posture upstream,
and here into register/warmth/hedging directives.

Calibration order (architecture doc §5.3):
    1. Mode base parameters
    2. Circadian adjustment (override / additive / subtractive)
    3. Relationship-stage register override
    4. User preferences (from RelationshipState, derived from the UWM comms model)
    5. BES negative-drift override
    6. Persona hard constraints (override everything)
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from typing import Optional

from backend.layer2_memory.schemas import ConversationMode
from backend.layer3_reasoning.schemas import BackgroundEmotionalState, BESLabel
from backend.layer4_persona.schemas import (
    HumorMode,
    PersonaState,
    Register,
    RelationshipStage,
    RelationshipState,
    SelfDisclosureDepth,
    VocabularyTier,
    VoiceParameters,
)

# ── Input 1: mode base parameters (architecture doc §5.3) ────────────────────
# Only the fields that differ from the VoiceParameters defaults are listed per mode.
MODE_BASE_PARAMETERS: dict[str, dict] = {
    ConversationMode.CRISIS.value: {
        "register": "natural", "sentence_length": "short",
        "warmth_expression": 0.9, "empathy_explicitness": 0.9, "validation_first": True,
        "humor_mode": "none", "follow_up_question_allowed": True,
        "follow_up_question_max": 1, "question_type": "checking_in",
        "target_response_length": "short", "max_response_length_chars": 400,
        "hedging_level": 0.1, "opinion_expression_allowed": False,
        "self_disclosure_allowed": False,
    },
    ConversationMode.EMOTIONAL_SUPPORT.value: {
        "register": "natural", "sentence_length": "medium",
        "warmth_expression": 0.85, "empathy_explicitness": 0.80, "validation_first": True,
        "humor_mode": "none", "follow_up_question_allowed": True,
        "follow_up_question_max": 1, "question_type": "open",
        "target_response_length": "short", "max_response_length_chars": 600,
        "hedging_level": 0.3, "opinion_expression_allowed": False,
        "self_disclosure_allowed": True,   # gated by relationship stage below
    },
    ConversationMode.CELEBRATION.value: {
        "register": "casual", "sentence_length": "short",
        "warmth_expression": 1.0, "empathy_explicitness": 0.5, "celebration_energy": 0.9,
        "validation_first": False, "humor_mode": "moderate",
        "follow_up_question_allowed": True, "follow_up_question_max": 2,
        "question_type": "specific", "target_response_length": "short",
        "max_response_length_chars": 400, "hedging_level": 0.0,
        "opinion_expression_allowed": True,
    },
    ConversationMode.TECHNICAL_DISCUSSION.value: {
        "register": "professional", "sentence_length": "medium",
        "warmth_expression": 0.4, "empathy_explicitness": 0.2, "validation_first": False,
        "humor_mode": "subtle", "follow_up_question_allowed": True,
        "follow_up_question_max": 1, "question_type": "specific",
        "target_response_length": "adaptive", "max_response_length_chars": 1200,
        "hedging_level": 0.2, "use_lists": True, "vocabulary_tier": "technical",
        "opinion_expression_allowed": True,
    },
    ConversationMode.GOAL_PLANNING.value: {
        "register": "professional", "sentence_length": "mixed",
        "warmth_expression": 0.6, "empathy_explicitness": 0.4, "validation_first": False,
        "humor_mode": "subtle", "follow_up_question_allowed": True,
        "follow_up_question_max": 2, "question_type": "specific",
        "target_response_length": "medium", "max_response_length_chars": 900,
        "hedging_level": 0.15, "use_lists": True, "opinion_expression_allowed": True,
    },
    ConversationMode.SOCIAL_COACHING.value: {
        "register": "natural", "sentence_length": "medium",
        "warmth_expression": 0.75, "empathy_explicitness": 0.70, "validation_first": True,
        "humor_mode": "none", "follow_up_question_allowed": True,
        "follow_up_question_max": 1, "question_type": "open",
        "target_response_length": "medium", "max_response_length_chars": 800,
        "hedging_level": 0.35, "opinion_expression_allowed": False,
    },
    ConversationMode.LIFE_REVIEW.value: {
        "register": "natural", "sentence_length": "long",
        "warmth_expression": 0.80, "empathy_explicitness": 0.65, "validation_first": False,
        "humor_mode": "subtle", "follow_up_question_allowed": True,
        "follow_up_question_max": 1, "question_type": "open",
        "target_response_length": "long", "max_response_length_chars": 1000,
        "hedging_level": 0.2, "opinion_expression_allowed": True,
    },
    ConversationMode.CASUAL.value: {
        "register": "casual", "sentence_length": "short",
        "warmth_expression": 0.65, "empathy_explicitness": 0.3, "validation_first": False,
        "humor_mode": "moderate", "follow_up_question_allowed": True,
        "follow_up_question_max": 1, "question_type": "open",
        "target_response_length": "short", "max_response_length_chars": 500,
        "hedging_level": 0.1, "opinion_expression_allowed": True,
    },
}

# ── Input 2: circadian adjustment (architecture doc §5.3) ────────────────────
CIRCADIAN_ADJUSTMENTS: dict[str, dict] = {
    "late_night": {
        "sentence_length": "short", "warmth_expression": 0.10,
        "humor_mode": "none", "max_response_length_chars": -200,
    },
    "early_morning": {"warmth_expression": 0.05, "celebration_energy": 0.05},
    "morning": {"sentence_length": "short", "hedging_level": -0.05},
    "evening": {},
    "afternoon": {},
    "night": {"warmth_expression": 0.05},
}

# Circadian fields whose numeric value is *added* rather than overwritten.
_ADDITIVE_CIRCADIAN_FIELDS = {
    "warmth_expression", "celebration_energy", "hedging_level",
    "max_response_length_chars",
}

# Register per relationship stage (architecture doc §5.3 Input 3).
_STAGE_REGISTER = {
    RelationshipStage.NEW.value: Register.PROFESSIONAL.value,
    RelationshipStage.ACQUAINTANCE.value: Register.NATURAL.value,
    RelationshipStage.DEVELOPING.value: Register.NATURAL.value,
    RelationshipStage.ESTABLISHED.value: Register.CASUAL.value,
    RelationshipStage.CLOSE.value: Register.INTIMATE.value,
}

# Modes whose register is warmth-critical and must stay "natural" regardless of stage.
_REGISTER_LOCKED_MODES = {
    ConversationMode.CRISIS.value,
    ConversationMode.EMOTIONAL_SUPPORT.value,
}

# BES labels that trigger the negative-drift override (architecture doc §5.3 Input 5).
_NEGATIVE_DRIFT_LABELS = {
    BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value,
    BESLabel.DETERIORATING.value,
}

# Disclosure-depth ranking for capping by relationship ceiling.
_DISCLOSURE_RANK = {"none": 0, "surface": 1, "moderate": 2, "deep": 3}

_FLOAT_FIELDS = {"warmth_expression", "empathy_explicitness", "celebration_energy",
                 "hedging_level"}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _apply_circadian(params: VoiceParameters, adjustments: dict) -> None:
    for fieldname, delta in adjustments.items():
        if fieldname in _ADDITIVE_CIRCADIAN_FIELDS:
            current = getattr(params, fieldname)
            updated = current + delta
            if fieldname == "max_response_length_chars":
                updated = max(200, int(updated))
            elif fieldname in _FLOAT_FIELDS:
                updated = _clamp01(updated)
            setattr(params, fieldname, updated)
        else:
            setattr(params, fieldname, delta)


def _apply_stage_register(
    params: VoiceParameters, relationship_state: RelationshipState, mode: str
) -> None:
    if mode in _REGISTER_LOCKED_MODES:
        return  # warmth-critical modes keep their natural register
    params.register = _STAGE_REGISTER.get(relationship_state.stage, params.register)


def _apply_user_preferences(
    params: VoiceParameters, relationship_state: RelationshipState
) -> None:
    pref = relationship_state.response_length_preference
    if pref >= 0.7:
        params.max_response_length_chars = int(params.max_response_length_chars + 200)
    elif pref <= 0.3:
        params.max_response_length_chars = max(200, int(params.max_response_length_chars - 150))


def _apply_bes_drift(params: VoiceParameters, background_state: BackgroundEmotionalState) -> None:
    if background_state.bes_label in _NEGATIVE_DRIFT_LABELS:
        params.warmth_expression = _clamp01(params.warmth_expression + 0.10)
        params.humor_mode = HumorMode.NONE.value
        params.max_response_length_chars = max(200, params.max_response_length_chars - 200)


def _apply_persona_constraints(
    params: VoiceParameters,
    persona_state: PersonaState,
    relationship_state: RelationshipState,
    mode: str,
) -> None:
    # Humor is gated by the persona (which already folded in mode + receptivity).
    if not persona_state.humor_allowed:
        params.humor_mode = HumorMode.NONE.value

    # Technical vocabulary requires the persona to permit it.
    if not persona_state.technical_depth_allowed:
        params.vocabulary_tier = VocabularyTier.STANDARD.value

    # Follow-up questions: relationship tolerance + stage ceiling both apply.
    if relationship_state.question_tolerance <= 0.3:
        params.follow_up_question_allowed = False
        params.follow_up_question_max = 0
    else:
        params.follow_up_question_max = min(
            params.follow_up_question_max, relationship_state.follow_up_question_ceiling
        )

    # Self-disclosure: mode may permit it, but the relationship stage caps the depth.
    ceiling = relationship_state.self_disclosure_ceiling
    ceiling_rank = _DISCLOSURE_RANK.get(ceiling, 1)
    if params.self_disclosure_allowed:
        # New/acquaintance (surface ceiling) cannot self-disclose meaningfully.
        params.self_disclosure_allowed = ceiling_rank >= _DISCLOSURE_RANK["moderate"]
    if params.self_disclosure_allowed:
        depth = min(ceiling_rank, _DISCLOSURE_RANK[SelfDisclosureDepth.MODERATE.value])
        params.self_disclosure_depth = {0: "none", 1: "surface", 2: "moderate"}[depth]
    else:
        params.self_disclosure_depth = SelfDisclosureDepth.NONE.value


def calibrate_voice(
    conversation_mode: str,
    circadian_band: str,
    relationship_state: RelationshipState,
    persona_state: PersonaState,
    background_state: BackgroundEmotionalState,
    communication_model=None,
) -> VoiceParameters:
    """Compute the deterministic ``VoiceParameters`` for this turn (architecture doc §5.3)."""
    params = VoiceParameters()

    # 1. Mode base (fall back to casual if an unknown mode slips through).
    base = MODE_BASE_PARAMETERS.get(
        conversation_mode, MODE_BASE_PARAMETERS[ConversationMode.CASUAL.value]
    )
    valid = {f.name for f in dataclass_fields(VoiceParameters)}
    for fieldname, value in base.items():
        if fieldname in valid:
            setattr(params, fieldname, value)

    # 2. Circadian adjustment.
    _apply_circadian(params, CIRCADIAN_ADJUSTMENTS.get(circadian_band, {}))

    # 3. Relationship-stage register override.
    _apply_stage_register(params, relationship_state, conversation_mode)

    # 4. User preferences.
    _apply_user_preferences(params, relationship_state)

    # 5. BES negative-drift override.
    _apply_bes_drift(params, background_state)

    # 6. Persona hard constraints (last; override everything).
    _apply_persona_constraints(params, persona_state, relationship_state, conversation_mode)

    return params
