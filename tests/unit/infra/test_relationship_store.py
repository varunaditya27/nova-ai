import pytest
pytest.importorskip("sqlalchemy")

from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.relationship_store import PostgresRelationshipStore, stage_for_sessions


def _store(user="u1"):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresRelationshipStore(make_session_factory(engine), user)


def test_default_state_is_new():
    rel = _store().load()
    assert rel.stage == "new" and rel.total_sessions == 0


def test_record_turn_increments_messages_and_counts_sessions():
    store = _store()
    store.record_turn("s1")
    store.record_turn("s1")   # same session → messages up, sessions flat
    store.record_turn("s2")   # new session
    rel = store.load()
    assert rel.total_messages_exchanged == 3
    assert rel.total_sessions == 2


def test_stage_advances_with_sessions():
    # Thresholds are the inclusive upper bound of each stage (relationship_manager.py,
    # now the single source of truth this store imports from -- a prior local duplicate
    # here treated 100 as the *floor* of "close" instead of the ceiling of "established").
    assert stage_for_sessions(0) == "new"
    assert stage_for_sessions(4) == "acquaintance"
    assert stage_for_sessions(16) == "developing"
    assert stage_for_sessions(41) == "established"
    assert stage_for_sessions(100) == "established"
    assert stage_for_sessions(101) == "close"


def test_stage_persisted_after_enough_sessions():
    store = _store()
    for i in range(4):
        store.record_turn(f"s{i}")
    assert store.load().stage == "acquaintance"


def test_is_user_scoped():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    f = make_session_factory(engine)
    PostgresRelationshipStore(f, "u1").record_turn("s1")
    assert PostgresRelationshipStore(f, "u2").load().total_messages_exchanged == 0


def test_record_turn_learns_communication_style():
    store = _store()
    for i in range(6):
        store.record_turn(f"s{i}", user_message="ok")     # terse messages
    rel = store.load()
    assert rel.response_length_preference < 0.4            # learned: prefers short replies


def test_record_turn_without_message_leaves_style_neutral():
    store = _store()
    store.record_turn("s1")                                 # no message → no learning
    assert store.load().response_length_preference == 0.5
