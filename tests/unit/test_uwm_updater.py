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


def test_silent_turn_is_a_no_op_even_when_a_uwm_already_exists():
    """A turn with nothing extracted must not bump update_version or write a no-op audit entry --
    only real signal should ever touch a persisted UWM (state_updater saves + audits whatever
    this function returns)."""
    uwm = UserWorldModel(user_id=uuid4(), update_version=3)
    assert merge_uwm_update(uwm, uwm.user_id, {}, NOW) is None
