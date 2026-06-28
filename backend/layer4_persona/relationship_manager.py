"""SC-2 — Relationship State Manager (architecture doc §4).

Computes the current relationship depth between Nova and the user: a structured,
multi-dimensional state (tie strength, stage, intimacy model, trust, communication
calibration). The stage is a strict behavioral *gate*, not a preference — it
defines what relational behaviors are available (§4.4, §14.3).

Deterministic, no LLM call (target < 3ms). Tie strength is persisted/updated by the
Layer 2 State Updater at session end; this manager reads it and optionally applies a
within-session increment. When no persisted state exists it falls back to the most
conservative ``new`` stage (§12).
"""

from __future__ import annotations

from typing import Optional

from backend.layer2_memory.schemas import CommunicationModel
from backend.layer4_persona.schemas import (
    MemoryReferencePolicy,
    RelationshipStage,
    RelationshipState,
    SelfDisclosureDepth,
    SessionSummary,
)

# Inclusive upper session counts for each stage (architecture doc §4.2).
_STAGE_THRESHOLDS = [
    (3, RelationshipStage.NEW.value),
    (15, RelationshipStage.ACQUAINTANCE.value),
    (40, RelationshipStage.DEVELOPING.value),
    (100, RelationshipStage.ESTABLISHED.value),
]

# Per-stage behavioral gates (architecture doc §4.4).
_STAGE_GATES: dict[str, dict] = {
    RelationshipStage.NEW.value: {
        "self_disclosure_ceiling": SelfDisclosureDepth.SURFACE.value,
        "memory_reference_policy": MemoryReferencePolicy.NONE.value,
        "follow_up_question_ceiling": 1,
        "direct_noticing_allowed": False,
    },
    RelationshipStage.ACQUAINTANCE.value: {
        "self_disclosure_ceiling": SelfDisclosureDepth.SURFACE.value,
        "memory_reference_policy": MemoryReferencePolicy.SOFT.value,
        "follow_up_question_ceiling": 2,
        "direct_noticing_allowed": False,
    },
    RelationshipStage.DEVELOPING.value: {
        "self_disclosure_ceiling": SelfDisclosureDepth.MODERATE.value,
        "memory_reference_policy": MemoryReferencePolicy.EPISODIC.value,
        "follow_up_question_ceiling": 3,
        "direct_noticing_allowed": False,   # "only if crisis" — crisis bypasses gating
    },
    RelationshipStage.ESTABLISHED.value: {
        "self_disclosure_ceiling": SelfDisclosureDepth.MODERATE.value,
        "memory_reference_policy": MemoryReferencePolicy.FULL.value,
        "follow_up_question_ceiling": 3,
        "direct_noticing_allowed": True,    # mismatch posture 1 allowed
    },
    RelationshipStage.CLOSE.value: {
        "self_disclosure_ceiling": "deep",  # beyond the SelfDisclosureDepth enum cap
        "memory_reference_policy": MemoryReferencePolicy.FULL.value,
        "follow_up_question_ceiling": 3,
        "direct_noticing_allowed": True,    # mismatch postures 1 + 2 allowed
    },
}

_LENGTH_PREF = {"short": 0.3, "terse": 0.2, "moderate": 0.5, "long": 0.8, "expansive": 0.9}


def stage_for_sessions(total_sessions: int) -> str:
    """Map a session count to its relationship stage (architecture doc §4.2)."""
    for threshold, stage in _STAGE_THRESHOLDS:
        if total_sessions <= threshold:
            return stage
    return RelationshipStage.CLOSE.value


def compute_session_delta(session_summary: SessionSummary) -> float:
    """Per-session tie-strength increment, capped at 0.08 (architecture doc §4.3)."""
    base = 0.02  # minimum increment for any session
    if session_summary.had_vulnerability_moment:
        base += 0.04
    base += session_summary.explicit_trust_signals_count * 0.01
    if session_summary.total_messages > 20:
        base += 0.01
    if session_summary.max_emotional_intensity > 0.6:
        base += 0.02
    if session_summary.repair_occurred:
        base += 0.03
    return min(base, 0.08)


def update_tie_strength(current: float, delta: float) -> float:
    """Asymptotic update: grows fast early, slows near 1.0 (architecture doc §4.3).

    ``TieStrength_{t+1} = TieStrength_t + delta * (1 - TieStrength_t)``.
    """
    updated = current + delta * (1.0 - current)
    return max(0.0, min(1.0, updated))


def _apply_stage_gates(state: RelationshipState) -> None:
    """Populate the behavioral-gate fields from the resolved stage (§4.4)."""
    gates = _STAGE_GATES[state.stage]
    state.self_disclosure_ceiling = gates["self_disclosure_ceiling"]
    state.memory_reference_policy = gates["memory_reference_policy"]
    state.follow_up_question_ceiling = gates["follow_up_question_ceiling"]
    state.direct_noticing_allowed = gates["direct_noticing_allowed"]


def _apply_style_calibration(
    state: RelationshipState, communication_model: Optional[CommunicationModel]
) -> None:
    """Derive communication-style calibration from the UWM communication model (§4.2)."""
    if communication_model is None:
        return
    length = (communication_model.typical_message_length or "moderate").lower()
    state.response_length_preference = _LENGTH_PREF.get(length, 0.5)
    state.question_tolerance = 0.7 if communication_model.engages_with_questions else 0.3
    state.unsolicited_advice_tolerance = (
        0.6 if communication_model.prefers_direct_answers else 0.4
    )
    state.formality_preference = 0.3 if communication_model.uses_slang else 0.5


def compute_relationship_state(
    persisted: Optional[RelationshipState] = None,
    session_summary: Optional[SessionSummary] = None,
    communication_model: Optional[CommunicationModel] = None,
) -> RelationshipState:
    """Assemble the current ``RelationshipState`` (architecture doc §4.2–4.4).

    Reads persisted tie strength / session counts, optionally applies a within-session
    increment from ``session_summary``, resolves the stage, and stamps the stage gates
    and communication-style calibration. Falls back to a fresh ``new`` state when no
    persisted relationship exists (§12).
    """
    if persisted is None:
        state = RelationshipState()
    else:
        # Shallow copy so we never mutate the caller's persisted record.
        state = RelationshipState(**vars(persisted))

    # Optional within-session tie-strength increment.
    if session_summary is not None:
        delta = compute_session_delta(session_summary)
        state.tie_strength = update_tie_strength(state.tie_strength, delta)
        state.vulnerability_moments += int(session_summary.had_vulnerability_moment)
        state.explicit_trust_signals += session_summary.explicit_trust_signals_count
        state.repair_events += int(session_summary.repair_occurred)

    state.stage = stage_for_sessions(state.total_sessions)
    _apply_stage_gates(state)
    _apply_style_calibration(state, communication_model)
    return state
