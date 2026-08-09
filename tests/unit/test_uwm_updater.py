"""Tests for the User World Model merge logic (architecture doc §7, backend/layer2_memory/uwm_updater.py)."""

from datetime import datetime
from uuid import uuid4

from backend.layer2_memory.schemas import UserWorldModel
from backend.layer2_memory.uwm_updater import merge_uwm_update

NOW = datetime(2026, 8, 5)


def test_creates_the_first_row_when_something_was_extracted():
    user = uuid4()
    uwm = merge_uwm_update(None, user, {"profile": {"preferred_name": "Sam"}}, NOW)
    assert uwm is not None
    assert uwm.user_id == user
    assert uwm.profile.preferred_name == "Sam"
    assert uwm.update_version == 1


def test_returns_none_when_nothing_exists_and_nothing_was_extracted():
    assert merge_uwm_update(None, uuid4(), {}, NOW) is None


def test_profile_fields_only_overwritten_when_a_value_is_present():
    uwm = UserWorldModel(user_id=uuid4())
    uwm.profile.preferred_name = "Sam"
    updated = merge_uwm_update(uwm, uwm.user_id, {"profile": {"current_life_stage": "grad student"}}, NOW)
    assert updated.profile.preferred_name == "Sam"          # untouched
    assert updated.profile.current_life_stage == "grad student"


def test_new_person_is_added_and_repeated_mentions_bump_count():
    uwm = UserWorldModel(user_id=uuid4())
    uwm = merge_uwm_update(uwm, uwm.user_id,
                           {"people": [{"name": "Maya", "relationship_tier": "friend"}]}, NOW)
    assert len(uwm.relationship_graph.people) == 1
    assert uwm.relationship_graph.people[0].mention_count == 1

    uwm = merge_uwm_update(uwm, uwm.user_id,
                           {"people": [{"name": "maya", "traits": ["supportive"]}]}, NOW)
    assert len(uwm.relationship_graph.people) == 1          # matched case-insensitively, not duped
    assert uwm.relationship_graph.people[0].mention_count == 2
    assert "supportive" in uwm.relationship_graph.people[0].inferred_traits


def test_situations_and_stressors_are_deduplicated_by_description():
    uwm = UserWorldModel(user_id=uuid4())
    delta = {"situations": [{"description": "Starting a new job", "category": "career"}],
             "stressors": [{"description": "Exam next week", "intensity": 0.7}]}
    uwm = merge_uwm_update(uwm, uwm.user_id, delta, NOW)
    uwm = merge_uwm_update(uwm, uwm.user_id, delta, NOW)   # same signals again next turn
    assert len(uwm.life_context.active_situations) == 1
    assert len(uwm.life_context.active_stressors) == 1


def test_update_version_and_data_sources_advance_on_real_signal():
    uwm = UserWorldModel(user_id=uuid4())
    uwm = merge_uwm_update(uwm, uwm.user_id, {"profile": {"pronouns": "she/her"}}, NOW)
    assert uwm.update_version == 1
    assert "api.uwm_updater" in uwm.data_sources
    uwm = merge_uwm_update(uwm, uwm.user_id, {"profile": {"location_context": "Mumbai"}}, NOW)
    assert uwm.update_version == 2
    assert uwm.data_sources.count("api.uwm_updater") == 1   # not duplicated on repeat calls


# ── Psychological model (§7, 2026-08-09) ─────────────────────────────────────
def test_psychological_signals_are_merged_and_deduplicated():
    uwm = UserWorldModel(user_id=uuid4())
    delta = {"psychological": {
        "attachment_signals": ["gets anxious when friends go quiet"],
        "emotional_regulation_style": "tends to withdraw",
        "preferred_support_style": "wants space before advice",
        "self_efficacy_signals": ["believes they can turn this around"],
        "identity_conflict_signals": ["unsure if this career still fits who they are"],
        "triggers": [{"description": "being compared to a sibling", "response_type": "shuts down"}],
    }}
    uwm = merge_uwm_update(uwm, uwm.user_id, delta, NOW)
    psych = uwm.psychological_model
    assert psych.attachment_signals == ["gets anxious when friends go quiet"]
    assert psych.emotional_regulation_style == "tends to withdraw"
    assert psych.preferred_support_style == "wants space before advice"
    assert psych.self_efficacy_signals == ["believes they can turn this around"]
    assert psych.identity_conflict_signals == ["unsure if this career still fits who they are"]
    assert len(psych.known_triggers) == 1
    assert psych.known_triggers[0].description == "being compared to a sibling"
    assert psych.known_triggers[0].response_type == "shuts down"
    assert psych.derived_from_episode_count == 1
    assert psych.last_updated == NOW

    # Repeating the same signals must not duplicate list entries or the trigger.
    uwm = merge_uwm_update(uwm, uwm.user_id, delta, NOW)
    assert len(uwm.psychological_model.attachment_signals) == 1
    assert len(uwm.psychological_model.known_triggers) == 1
    assert uwm.psychological_model.derived_from_episode_count == 2


def test_psychological_model_absent_key_is_a_no_op():
    uwm = UserWorldModel(user_id=uuid4())
    uwm = merge_uwm_update(uwm, uwm.user_id, {"profile": {"pronouns": "they/them"}}, NOW)
    assert uwm.psychological_model.derived_from_episode_count == 0
    assert uwm.psychological_model.known_triggers == []


def test_psychological_model_round_trips_through_serde():
    # known_triggers is list[TriggerPattern] -- the bare-list serde bug has bitten this codebase
    # four times already (Layers 7/9/10/13); prove the nested dataclass survives a real round trip.
    from infra.db.memory_serde import from_jsonable, to_jsonable

    uwm = UserWorldModel(user_id=uuid4())
    uwm = merge_uwm_update(uwm, uwm.user_id, {"psychological": {
        "triggers": [{"description": "unexpected schedule changes", "response_type": "gets irritable"}],
    }}, NOW)
    payload = to_jsonable(uwm)
    restored = from_jsonable(UserWorldModel, payload)
    assert len(restored.psychological_model.known_triggers) == 1
    trigger = restored.psychological_model.known_triggers[0]
    assert trigger.description == "unexpected schedule changes"
    assert trigger.response_type == "gets irritable"
    assert trigger.trigger_id == uwm.psychological_model.known_triggers[0].trigger_id


def test_silent_turn_is_a_no_op_even_when_a_uwm_already_exists():
    """A turn with nothing extracted must not bump update_version or write a no-op audit entry --
    only real signal should ever touch a persisted UWM (state_updater saves + audits whatever
    this function returns)."""
    uwm = UserWorldModel(user_id=uuid4(), update_version=3)
    assert merge_uwm_update(uwm, uwm.user_id, {}, NOW) is None
