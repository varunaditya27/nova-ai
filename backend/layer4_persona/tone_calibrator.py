"""SC-3 — Tone & Style Calibrator (architecture doc §5).

Takes the PersonaState, RelationshipState, and the upstream emotional context and
produces a ``VoiceParameters`` struct — the precise, plain-language style directives
injected into the Semantic Planner and Emotion Refiner prompts.

Fully deterministic; no LLM call (target < 2ms). This is the layer that translates
numbers into language (design principle §14.4): valence/arousal floats never reach
the LLM — they have already been turned into a conversation mode and posture upstream,
and here into register/warmth/hedging directives.

Calibration order (architecture doc §5.3):
    1. Mode base parameters                       (tone_tables.py)
    2. Circadian adjustment (override/additive)    (tone_tables.py)
    3. Relationship-stage register override        (tone_tables.py)
    4. User preferences (from RelationshipState, derived from the UWM comms model)
    5. BES negative-drift override
    6. Persona hard constraints (override everything)
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields

from backend.layer2_memory.schemas import ConversationMode
from backend.layer3_reasoning.schemas import BackgroundEmotionalState, BESLabel
from backend.layer4_persona.schemas import (
    HumorMode,
    PersonaState,
    RelationshipState,
    SelfDisclosureDepth,
    VocabularyTier,
    VoiceParameters,
)
from backend.layer4_persona.tone_tables import (
    CIRCADIAN_ADJUSTMENTS,
    MODE_BASE_PARAMETERS,
    _clamp01,
    apply_circadian,
    apply_stage_register,
)

# BES labels that trigger the negative-drift override (architecture doc §5.3 Input 5).
_NEGATIVE_DRIFT_LABELS = {
    BESLabel.SIGNIFICANT_NEGATIVE_DRIFT.value,
    BESLabel.DETERIORATING.value,
}

# Disclosure-depth ranking for capping by relationship ceiling.
_DISCLOSURE_RANK = {"none": 0, "surface": 1, "moderate": 2, "deep": 3}


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
    apply_circadian(params, CIRCADIAN_ADJUSTMENTS.get(circadian_band, {}))

    # 3. Relationship-stage register override.
    apply_stage_register(params, relationship_state, conversation_mode)

    # 4. User preferences.
    _apply_user_preferences(params, relationship_state)

    # 5. BES negative-drift override.
    _apply_bes_drift(params, background_state)

    # 6. Persona hard constraints (last; override everything).
    _apply_persona_constraints(params, persona_state, relationship_state, conversation_mode)

    return params
