import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory.schemas import (
    EpisodicMemory, SemanticMemory, IdentityMemory, UserWorldModel, PersonNode,
)
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore


def _store():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresMemoryStore(make_session_factory(engine))


def test_episodic_save_get_and_active_filtering():
    store = _store()
    live = EpisodicMemory(user_id="u1", summary="live", created_at=datetime.now(timezone.utc))
    dead = EpisodicMemory(user_id="u1", summary="dead", is_deleted=True)
    arch = EpisodicMemory(user_id="u1", summary="arch", is_archived=True)
    for m in (live, dead, arch):
        store.save_episodic(m)
    assert store.get_episodic(live.memory_id).summary == "live"
    assert {m.summary for m in store.active_episodic("u1")} == {"live"}
    assert len(store.all_episodic("u1")) == 3


def test_cross_user_isolation():
    store = _store()
    store.save_episodic(EpisodicMemory(user_id="u1", summary="a"))
    store.save_episodic(EpisodicMemory(user_id="u2", summary="b"))
    assert {m.summary for m in store.active_episodic("u1")} == {"a"}


def test_memory_id_upsert_replaces_not_duplicates():
    store = _store()
    m = EpisodicMemory(user_id="u1", summary="v1")
    store.save_episodic(m)
    m.summary = "v2"
    m.S_current = 0.5
    store.save_episodic(m)
    active = store.active_episodic("u1")
    assert len(active) == 1 and active[0].summary == "v2" and active[0].S_current == 0.5


def test_semantic_active_and_candidates():
    store = _store()
    store.save_semantic(SemanticMemory(user_id="u1", statement="s-live"))
    store.save_semantic(SemanticMemory(user_id="u1", statement="s-dead", is_deprecated=True))
    store.save_episodic(EpisodicMemory(user_id="u1", summary="e-live"))
    assert {s.statement for s in store.active_semantic("u1")} == {"s-live"}
    assert len(store.candidate_memories("u1")) == 2  # 1 episodic + 1 semantic


def test_identity_is_cross_user():
    store = _store()
    store.save_identity(IdentityMemory(statement="values honesty", is_immutable=True))
    beliefs = store.identity_beliefs()
    assert len(beliefs) == 1 and beliefs[0].statement == "values honesty"


def test_uwm_save_load_and_query():
    store = _store()
    uid = uuid4()
    uwm = UserWorldModel(user_id=uid)
    uwm.relationship_graph.people.append(PersonNode(name="Sam", aliases=["Sammy"]))
    store.save_uwm(uwm)
    loaded = store.load_uwm(str(uid))
    assert loaded is not None and loaded.relationship_graph.people[0].name == "Sam"
    res = store.query_uwm(str(uid), "relationship_context", "talking to Sammy today")
    assert [p.name for p in res["relevant_people"]] == ["Sam"]
    assert store.load_uwm("nobody") is None
