"""Tests for SC-2 Relationship State Manager (architecture doc §4)."""

from backend.layer4_persona import relationship_manager as rm
from backend.layer4_persona.schemas import (
    MemoryReferencePolicy,
    RelationshipStage,
    RelationshipState,
    SessionSummary,
)
from backend.layer2_memory.schemas import CommunicationModel


# ── Stage gating from session count (§4.2) ───────────────────────────────────
def test_stage_boundaries():
    assert rm.stage_for_sessions(0) == RelationshipStage.NEW.value
    assert rm.stage_for_sessions(3) == RelationshipStage.NEW.value
    assert rm.stage_for_sessions(4) == RelationshipStage.ACQUAINTANCE.value
    assert rm.stage_for_sessions(15) == RelationshipStage.ACQUAINTANCE.value
    assert rm.stage_for_sessions(16) == RelationshipStage.DEVELOPING.value
    assert rm.stage_for_sessions(40) == RelationshipStage.DEVELOPING.value
    assert rm.stage_for_sessions(41) == RelationshipStage.ESTABLISHED.value
    assert rm.stage_for_sessions(100) == RelationshipStage.ESTABLISHED.value
    assert rm.stage_for_sessions(101) == RelationshipStage.CLOSE.value


# ── Tie strength session delta (§4.3) ────────────────────────────────────────
def test_session_delta_base_minimum():
    assert abs(rm.compute_session_delta(SessionSummary()) - 0.02) < 1e-9


def test_session_delta_accumulates_signals():
    s = SessionSummary(had_vulnerability_moment=True, explicit_trust_signals_count=1,
                       total_messages=25, max_emotional_intensity=0.7, repair_occurred=True)
    # 0.02 + 0.04 + 0.01 + 0.01 + 0.02 + 0.03 = 0.13 → capped at 0.08
    assert abs(rm.compute_session_delta(s) - 0.08) < 1e-9


def test_session_delta_capped_at_max():
    s = SessionSummary(explicit_trust_signals_count=50)
    assert rm.compute_session_delta(s) == 0.08


# ── Asymptotic tie-strength update (§4.3) ────────────────────────────────────
def test_update_tie_strength_grows_fast_early_slows_late():
    low = rm.update_tie_strength(0.0, 0.08)
    high = rm.update_tie_strength(0.9, 0.08)
    assert abs(low - 0.08) < 1e-9          # from zero, delta applies fully
    assert high > 0.9 and (high - 0.9) < 0.08   # near ceiling, increment shrinks
    assert high <= 1.0


def test_update_tie_strength_never_exceeds_one():
    assert rm.update_tie_strength(0.99, 0.08) <= 1.0


# ── Stage gates (§4.4) ───────────────────────────────────────────────────────
def test_new_stage_gates_are_most_conservative():
    state = rm.compute_relationship_state(persisted=RelationshipState(total_sessions=1))
    assert state.stage == RelationshipStage.NEW.value
    assert state.memory_reference_policy == MemoryReferencePolicy.NONE.value
    assert state.direct_noticing_allowed is False
    assert state.self_disclosure_ceiling == "surface"
    assert state.follow_up_question_ceiling == 1


def test_close_stage_gates_are_open():
    state = rm.compute_relationship_state(persisted=RelationshipState(total_sessions=150))
    assert state.stage == RelationshipStage.CLOSE.value
    assert state.memory_reference_policy == MemoryReferencePolicy.FULL.value
    assert state.direct_noticing_allowed is True
    assert state.self_disclosure_ceiling == "deep"
    assert state.follow_up_question_ceiling >= 2


def test_developing_allows_episodic_memory_not_direct_noticing():
    state = rm.compute_relationship_state(persisted=RelationshipState(total_sessions=20))
    assert state.stage == RelationshipStage.DEVELOPING.value
    assert state.memory_reference_policy == MemoryReferencePolicy.EPISODIC.value
    assert state.direct_noticing_allowed is False


# ── Within-session increment + recompute (§4.3) ──────────────────────────────
def test_within_session_increment_raises_tie_strength():
    persisted = RelationshipState(tie_strength=0.30, total_sessions=10)
    summary = SessionSummary(had_vulnerability_moment=True, total_messages=30)
    state = rm.compute_relationship_state(persisted=persisted, session_summary=summary)
    assert state.tie_strength > 0.30


# ── Style calibration from CommunicationModel (§4.2) ─────────────────────────
def test_style_calibration_from_communication_model():
    comms = CommunicationModel(typical_message_length="long", engages_with_questions=True,
                               uses_slang=True)
    terse = CommunicationModel(typical_message_length="short", engages_with_questions=False)
    expansive = rm.compute_relationship_state(
        persisted=RelationshipState(total_sessions=10), communication_model=comms)
    short = rm.compute_relationship_state(
        persisted=RelationshipState(total_sessions=10), communication_model=terse)
    assert expansive.response_length_preference > short.response_length_preference
    assert expansive.question_tolerance > short.question_tolerance


# ── §12 fallback: relationship state unavailable → new, conservative ─────────
def test_fallback_to_new_when_unavailable():
    state = rm.compute_relationship_state(persisted=None)
    assert state.stage == RelationshipStage.NEW.value
    assert state.memory_reference_policy == MemoryReferencePolicy.NONE.value
    assert state.direct_noticing_allowed is False
