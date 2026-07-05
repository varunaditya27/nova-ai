import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime

from infra.db.base import Base
from infra.db.engine import make_engine, make_session_factory, session_scope, init_db
import infra.db.models as models


EXPECTED_TABLES = {
    "session", "episodic_memory", "semantic_memory", "identity_memory", "memory_audit",
    "user_world_model", "persona_state", "relationship_state", "goal", "proactive_item",
    "safety_event", "privacy_audit", "longitudinal_summary", "tool_action", "output_pref",
    "onboarding_state",
}


def test_all_tables_registered():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_episodic_payload_roundtrip():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.EpisodicMemory(user_id="u1", memory_id="m1",
                                    payload={"summary": "first chat"}))
    with session_scope(factory) as s:
        row = s.query(models.EpisodicMemory).filter_by(memory_id="m1").one()
        assert row.payload["summary"] == "first chat"
        assert row.is_deleted is False and row.is_archived is False
        assert isinstance(row.created_at, datetime)


def test_user_world_model_one_per_user():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.UserWorldModel(user_id="u1", payload={"update_version": 0}))
    with session_scope(factory) as s:
        assert s.query(models.UserWorldModel).filter_by(user_id="u1").one().payload["update_version"] == 0


def test_memory_audit_payload_shape():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.MemoryAudit(user_id="u1", entry_hash="h1", prev_hash=None,
                                 event_type="memory_created", payload={"reason": "x"}))
    with session_scope(factory) as s:
        row = s.query(models.MemoryAudit).filter_by(entry_hash="h1").one()
        assert row.event_type == "memory_created" and row.payload["reason"] == "x"
        assert row.prev_hash is None


def test_onboarding_state_payload_shape():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.OnboardingState(user_id="u1", cold_start_active=True,
                                     payload={"session_index": 0}))
    with session_scope(factory) as s:
        row = s.query(models.OnboardingState).filter_by(user_id="u1").one()
        assert row.cold_start_active is True and row.payload["session_index"] == 0


def test_safety_event_payload_shape():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.SafetyEvent(user_id="u1", tier="tier_2", resolved=False,
                                 payload={"confidence": 0.7}))
    with session_scope(factory) as s:
        row = s.query(models.SafetyEvent).filter_by(tier="tier_2").one()
        assert row.payload["confidence"] == 0.7 and row.resolved is False


def test_goal_model_has_status_and_user_scope():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.Goal(user_id="u1", goal_id="g1", status="active",
                          payload={"title": "run 5k"}))
    with session_scope(factory) as s:
        row = s.query(models.Goal).filter_by(goal_id="g1").one()
        assert row.status == "active" and row.payload["title"] == "run 5k"
        assert s.query(models.Goal).filter_by(status="active").count() == 1
