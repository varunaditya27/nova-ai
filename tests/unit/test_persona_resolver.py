"""Tests for SC-1 Persona State Resolver (architecture doc §3)."""

from backend.layer4_persona import persona_resolver as pr
from backend.layer4_persona.schemas import (
    DynamicPersonaProperty,
    PersonaState,
)
from backend.layer2_memory.schemas import (
    CommunicationModel,
    PsychologicalModel,
    TriggerPattern,
)
from backend.layer2_memory.schemas import ConversationMode


# ── Core anchors (§3.2) ──────────────────────────────────────────────────────
def test_core_anchors_present_and_name_immutable():
    anchors = pr.load_core_anchors(identity_memory_entries=None)
    assert anchors["name"]["value"] == "Nova"
    assert anchors["name"]["immutable"] is True
    # Every core anchor is high-centrality (>= 0.80) per §3.2.
    assert all(a["centrality"] >= 0.80 for a in anchors.values())


# ── Default resolution (§3.4 + §12 fallback) ─────────────────────────────────
def test_resolve_defaults_when_no_uwm_available():
    state = pr.resolve_persona_state()
    assert isinstance(state, PersonaState)
    assert state.name == "Nova"
    assert state.character_description          # assembled from core anchors
    assert state.core_anchors_loaded == len(pr.CORE_IDENTITY_ANCHORS)


def test_boundary_policies_are_always_true():
    # §11 hard rules: these cannot be turned off by any input.
    state = pr.resolve_persona_state(
        communication_model=CommunicationModel(uses_humor=True),
        psychological_model=PsychologicalModel(preferred_support_style="solution_oriented"))
    assert state.will_not_fabricate_emotions is True
    assert state.will_not_be_sycophantic is True
    assert state.will_disagree_when_warranted is True
    assert state.will_not_catastrophize is True


# ── Humor gating (§3.4) ──────────────────────────────────────────────────────
def test_humor_allowed_when_receptive_and_casual_mode():
    state = pr.resolve_persona_state(
        communication_model=CommunicationModel(uses_humor=True),
        session_context={"conversation_mode": ConversationMode.CASUAL.value})
    assert state.humor_allowed is True


def test_humor_suppressed_in_emotional_support_mode():
    state = pr.resolve_persona_state(
        communication_model=CommunicationModel(uses_humor=True),
        session_context={"conversation_mode": ConversationMode.EMOTIONAL_SUPPORT.value})
    assert state.humor_allowed is False


def test_humor_disallowed_when_user_not_receptive():
    state = pr.resolve_persona_state(
        communication_model=CommunicationModel(uses_humor=False),
        session_context={"conversation_mode": ConversationMode.CASUAL.value})
    assert state.humor_allowed is False


# ── Derived expression parameters (§3.4 reconciliation) ──────────────────────
def test_directness_from_communication_model():
    direct = pr.resolve_persona_state(
        communication_model=CommunicationModel(prefers_direct_answers=True))
    indirect = pr.resolve_persona_state(
        communication_model=CommunicationModel(prefers_direct_answers=False))
    assert direct.directness_level > indirect.directness_level


def test_technical_depth_from_vocabulary_complexity():
    techy = pr.resolve_persona_state(
        communication_model=CommunicationModel(vocabulary_complexity="high"))
    plain = pr.resolve_persona_state(
        communication_model=CommunicationModel(vocabulary_complexity="moderate"))
    assert techy.technical_depth_allowed is True
    assert plain.technical_depth_allowed is False


def test_known_sensitivities_derived_from_triggers():
    psych = PsychologicalModel(known_triggers=[
        TriggerPattern(description="mention of late father"),
        TriggerPattern(description="job rejection talk"),
    ])
    state = pr.resolve_persona_state(psychological_model=psych)
    assert "mention of late father" in state.known_sensitivities
    assert len(state.known_sensitivities) == 2


# ── Dynamic property overrides (§3.3) ────────────────────────────────────────
def test_dynamic_property_overrides_humor_frequency():
    dyn = {"humor_frequency_with_this_user": DynamicPersonaProperty(
        key="humor_frequency_with_this_user", value="0.6", confidence=0.8)}
    state = pr.resolve_persona_state(
        communication_model=CommunicationModel(uses_humor=True),
        dynamic_properties=dyn,
        session_context={"conversation_mode": ConversationMode.CASUAL.value})
    assert abs(state.humor_frequency - 0.6) < 1e-9
    assert state.dynamic_properties_loaded == 1


def test_dynamic_directness_calibration_overrides_default():
    dyn = {"directness_calibration": DynamicPersonaProperty(
        key="directness_calibration", value="0.9", confidence=0.9)}
    state = pr.resolve_persona_state(dynamic_properties=dyn)
    assert abs(state.directness_level - 0.9) < 1e-9
