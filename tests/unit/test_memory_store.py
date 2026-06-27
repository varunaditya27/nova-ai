"""Tests for the in-memory memory store + UWM query interface (architecture doc §7.9, §11)."""

from datetime import datetime
from uuid import uuid4

from backend.layer2_memory.memory_store import InMemoryMemoryStore
from backend.layer2_memory.schemas import (
    CommunicationModel,
    EpisodicMemory,
    LifeContext,
    LifeSituation,
    PersonNode,
    RelationshipGraph,
    SemanticMemory,
    Stressor,
    UserWorldModel,
)

USER = uuid4()


def test_save_and_get_episodic():
    store = InMemoryMemoryStore()
    mem = EpisodicMemory(user_id=USER, summary="interview went well")
    store.save_episodic(mem)
    assert store.get_episodic(mem.memory_id) is mem


def test_active_episodic_excludes_deleted_and_archived():
    store = InMemoryMemoryStore()
    live = EpisodicMemory(user_id=USER, summary="live")
    deleted = EpisodicMemory(user_id=USER, summary="gone", is_deleted=True)
    archived = EpisodicMemory(user_id=USER, summary="old", is_archived=True)
    for m in (live, deleted, archived):
        store.save_episodic(m)
    active = store.active_episodic(USER)
    assert live in active and deleted not in active and archived not in active


def test_candidate_memories_includes_active_episodic_and_semantic():
    store = InMemoryMemoryStore()
    ep = EpisodicMemory(user_id=USER, summary="ep")
    sem = SemanticMemory(user_id=USER, statement="stable fact")
    deprecated = SemanticMemory(user_id=USER, statement="old belief", is_deprecated=True)
    store.save_episodic(ep)
    store.save_semantic(sem)
    store.save_semantic(deprecated)
    candidates = store.candidate_memories(USER)
    assert ep in candidates and sem in candidates and deprecated not in candidates


def test_save_and_load_uwm():
    store = InMemoryMemoryStore()
    uwm = UserWorldModel(user_id=USER)
    store.save_uwm(uwm)
    assert store.load_uwm(USER) is uwm
    assert store.load_uwm(uuid4()) is None


def _uwm_with_world():
    rohan = PersonNode(name="Rohan", relationship_tier="close_friend",
                       emotional_significance_to_user=0.8)
    return UserWorldModel(
        user_id=USER,
        relationship_graph=RelationshipGraph(user_id=USER, people=[rohan]),
        life_context=LifeContext(
            active_stressors=[Stressor(description="placements", intensity=0.7)],
            active_situations=[LifeSituation(description="final year")],
        ),
        communication_model=CommunicationModel(prefers_direct_answers=True),
    )


def test_query_uwm_relationship_context_matches_names():
    store = InMemoryMemoryStore()
    store.save_uwm(_uwm_with_world())
    result = store.query_uwm(USER, "relationship_context", context="I talked to Rohan today")
    assert any(p.name == "Rohan" for p in result["relevant_people"])


def test_query_uwm_active_stressors():
    store = InMemoryMemoryStore()
    store.save_uwm(_uwm_with_world())
    result = store.query_uwm(USER, "active_stressors")
    assert result["active_stressors"][0].description == "placements"


def test_query_uwm_communication_preferences():
    store = InMemoryMemoryStore()
    store.save_uwm(_uwm_with_world())
    result = store.query_uwm(USER, "communication_preferences")
    assert result["communication_preferences"].prefers_direct_answers is True


def test_query_uwm_missing_user_returns_empty():
    store = InMemoryMemoryStore()
    assert store.query_uwm(uuid4(), "active_stressors") == {"active_stressors": []}
