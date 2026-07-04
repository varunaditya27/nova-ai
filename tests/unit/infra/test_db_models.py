import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime

from infra.db.base import Base
from infra.db.engine import make_engine, make_session_factory, session_scope, init_db
import infra.db.models as models


EXPECTED_TABLES = {
    "session", "episodic_memory", "semantic_memory", "identity_memory", "memory_audit",
    "persona_state", "relationship_state", "goal", "proactive_item", "safety_event",
    "privacy_audit", "longitudinal_summary", "tool_action", "output_pref", "onboarding_state",
}


def test_all_tables_registered():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_create_all_and_insert_roundtrip():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.EpisodicMemory(user_id="u1", summary="first chat", importance=0.5))
    with session_scope(factory) as s:
        row = s.query(models.EpisodicMemory).filter_by(user_id="u1").one()
        assert row.summary == "first chat"
        assert isinstance(row.created_at, datetime)


def test_goal_model_has_status_and_user_scope():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.Goal(user_id="u1", description="run 5k", status="active"))
    with session_scope(factory) as s:
        assert s.query(models.Goal).filter_by(status="active").count() == 1
