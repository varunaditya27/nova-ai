"""SC-3 Tone & Style Calibrator — mode/circadian/stage lookup tables (architecture doc §5.3
Inputs 1–3).

Split out of ``tone_calibrator.py``: static data + the apply-functions that read it,
distinct from the preference/BES/persona-constraint logic and the orchestrator.
"""

from __future__ import annotations

from backend.layer2_memory.schemas import ConversationMode
from backend.layer4_persona.schemas import Register, RelationshipStage, RelationshipState, VoiceParameters

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
_FLOAT_FIELDS = {"warmth_expression", "empathy_explicitness", "celebration_energy",
                 "hedging_level"}

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


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def apply_circadian(params: VoiceParameters, adjustments: dict) -> None:
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


def apply_stage_register(
    params: VoiceParameters, relationship_state: RelationshipState, mode: str
) -> None:
    if mode in _REGISTER_LOCKED_MODES:
        return  # warmth-critical modes keep their natural register
    params.register = _STAGE_REGISTER.get(relationship_state.stage, params.register)
