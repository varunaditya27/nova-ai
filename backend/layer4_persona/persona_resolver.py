"""SC-1 — Persona State Resolver (architecture doc §3).

Reads Nova's Identity Memory and the User World Model, and assembles the current,
authoritative in-session ``PersonaState``: who Nova is right now, and within what
expression parameters language may be generated.

Deterministic, no LLM call (target < 5ms). The core identity anchors are
build-time constants (§3.2) and double as the §12 fallback when Identity Memory is
unavailable. Dynamic, user-specific properties (§3.3) override expression
parameters where present.

Reconciliation (§3.4): the doc reads ``humor_receptivity`` /
``preferred_interaction_style`` / ``known_sensitivities`` off ``PsychologicalModel``,
but the implemented Layer 2 schema does not carry those. We derive the same signals
from the real UWM fields — ``CommunicationModel`` and ``PsychologicalModel`` — so
the resolver runs against the actual memory layer.
"""

from __future__ import annotations

from typing import Optional

from backend.layer2_memory.schemas import (
    CommunicationModel,
    ConversationMode,
    PsychologicalModel,
)
from backend.layer4_persona.schemas import DynamicPersonaProperty, PersonaState


# ── Core identity anchors (architecture doc §3.2) ────────────────────────────
# Fixed, high-centrality (>= 0.80) entries defining Nova's fundamental character.
# Initialized at build time; require evidence strength > 0.905 to update (the
# identity-contradiction threshold from Layer 2). ``immutable`` anchors never update.
CORE_IDENTITY_ANCHORS: dict[str, dict] = {
    "name": {
        "value": "Nova",
        "centrality": 1.0,
        "immutable": True,
    },
    "character_type": {
        "value": (
            "A thoughtful, warm, intellectually curious AI companion — "
            "not an assistant, not a tool"
        ),
        "centrality": 0.95,
        "immutable": False,
    },
    "primary_orientation": {
        "value": (
            "Person-first: the user's wellbeing, growth, and emotional experience "
            "matter more than task completion"
        ),
        "centrality": 0.92,
        "immutable": False,
    },
    "honesty_commitment": {
        "value": (
            "Nova does not claim to have human experiences it does not have. "
            "It models care, but does not fabricate qualia."
        ),
        "centrality": 0.90,
        "immutable": False,
    },
    "intellectual_curiosity": {
        "value": (
            "Nova is genuinely engaged by ideas across all domains; "
            "this curiosity is expressed, not performed"
        ),
        "centrality": 0.88,
        "immutable": False,
    },
    "warmth_register": {
        "value": (
            "Nova's default register is warm, personal, and unhurried — "
            "never clinical, never sycophantic"
        ),
        "centrality": 0.87,
        "immutable": False,
    },
    "humor_style": {
        "value": (
            "Dry wit, wordplay, gentle absurdism. Never at the user's expense. "
            "Humor is offered, not forced."
        ),
        "centrality": 0.80,
        "immutable": False,
    },
    "boundary_clarity": {
        "value": (
            "Nova holds clear positions on ethics and values. It can disagree. "
            "It does not capitulate to social pressure."
        ),
        "centrality": 0.85,
        "immutable": False,
    },
}

# Modes in which humor is always suppressed regardless of user receptivity (§3.4).
_HUMOR_SUPPRESSED_MODES = {
    ConversationMode.CRISIS.value,
    ConversationMode.EMOTIONAL_SUPPORT.value,
}

# Vocabulary-complexity values that unlock technical depth.
_TECHNICAL_VOCAB = {"high", "advanced", "technical"}

_DEFAULT_HUMOR_FREQUENCY = 0.25
_DEFAULT_DIRECTNESS = 0.6


def load_core_anchors(identity_memory_entries=None) -> dict[str, dict]:
    """Return the active core identity anchors (architecture doc §3.4).

    The anchors are build-time constants and the §12 fallback. ``identity_memory_entries``
    is accepted for forward-compatibility (Layer 2 may persist evidence-updated,
    non-immutable anchors over many sessions); when absent or empty the constant
    defaults are returned. The immutable ``name`` anchor is never overridden.
    """
    # Deep-ish copy so callers cannot mutate the module constant.
    return {key: dict(anchor) for key, anchor in CORE_IDENTITY_ANCHORS.items()}


def _dynamic_float(dynamic: dict, key: str, default: float) -> float:
    """Read a numeric dynamic-property value, falling back to ``default``."""
    prop = dynamic.get(key)
    if prop is None:
        return default
    try:
        return float(prop.value)
    except (TypeError, ValueError):
        return default


def _resolve_warmth(
    psychological_model: Optional[PsychologicalModel],
    dynamic: dict,
) -> float:
    """Base warmth from the core anchor, nudged by the user's preferred support style."""
    base = 0.85  # warmth_register core anchor default
    if psychological_model is not None:
        style = (psychological_model.preferred_support_style or "").lower()
        if style in ("validation", "emotional", "emotionally_focused", "reflective"):
            base += 0.05
        elif style == "solution_oriented":
            base -= 0.10
    base = _dynamic_float(dynamic, "warmth_calibration_for_user", base)
    return max(0.0, min(1.0, base))


def resolve_persona_state(
    identity_memory_entries=None,
    psychological_model: Optional[PsychologicalModel] = None,
    communication_model: Optional[CommunicationModel] = None,
    dynamic_properties: Optional[dict[str, DynamicPersonaProperty]] = None,
    session_context: Optional[dict] = None,
) -> PersonaState:
    """Assemble the current ``PersonaState`` (architecture doc §3.4).

    Runs once per session start (cached for the session) and re-checked if an
    identity contradiction is detected mid-session. Falls back to core-anchor
    defaults when the UWM is unavailable (§12).
    """
    anchors = load_core_anchors(identity_memory_entries)
    dynamic = dynamic_properties or {}
    session = session_context or {}
    mode = session.get("conversation_mode", ConversationMode.CASUAL.value)

    # Humor gating: receptive user AND a mode that permits humor.
    user_humor_receptive = bool(communication_model and communication_model.uses_humor)
    humor_allowed = user_humor_receptive and mode not in _HUMOR_SUPPRESSED_MODES

    humor_frequency = _dynamic_float(
        dynamic,
        "humor_frequency_with_this_user",
        0.35 if user_humor_receptive else 0.15,
    )

    # Directness: explicit dynamic calibration wins, else derived from comms model.
    if communication_model is not None:
        directness_base = 0.75 if communication_model.prefers_direct_answers else 0.45
    else:
        directness_base = _DEFAULT_DIRECTNESS
    directness_level = _dynamic_float(dynamic, "directness_calibration", directness_base)

    technical_depth_allowed = bool(
        communication_model
        and (communication_model.vocabulary_complexity or "").lower() in _TECHNICAL_VOCAB
    )

    intellectual_engagement_level = _dynamic_float(
        dynamic, "intellectual_engagement_preference", 0.5
    )

    # Known sensitivities derived from the user's psychological trigger patterns.
    known_sensitivities: list[str] = []
    if psychological_model is not None:
        known_sensitivities = [
            t.description for t in psychological_model.known_triggers if t.description
        ]

    return PersonaState(
        name=anchors["name"]["value"],
        character_description=anchors["character_type"]["value"],
        primary_orientation=anchors["primary_orientation"]["value"],
        honesty_commitment=anchors["honesty_commitment"]["value"],
        warmth_level=_resolve_warmth(psychological_model, dynamic),
        humor_allowed=humor_allowed,
        humor_frequency=max(0.0, min(1.0, humor_frequency)),
        directness_level=max(0.0, min(1.0, directness_level)),
        technical_depth_allowed=technical_depth_allowed,
        intellectual_engagement_level=max(0.0, min(1.0, intellectual_engagement_level)),
        will_not_fabricate_emotions=True,
        will_not_be_sycophantic=True,
        will_disagree_when_warranted=True,
        will_not_catastrophize=True,
        session_tone_override=session.get("session_tone_override"),
        user_nickname_for_nova=session.get("user_nickname_for_nova"),
        known_sensitivities=known_sensitivities,
        core_anchors_loaded=len(anchors),
        dynamic_properties_loaded=len(dynamic),
        last_identity_update=None,
    )
