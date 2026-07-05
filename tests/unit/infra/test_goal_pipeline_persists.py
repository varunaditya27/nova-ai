import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer7_goals import run_goal_pipeline
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.goal_store import PostgresGoalStore


def _factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def test_new_goal_extracted_and_persisted():
    f = _factory()
    now = datetime.now(timezone.utc)

    def fake_llm(_prompt):
        return {"goal_detected": True,
                "new_goal": {"inferred_title": "run a 5k", "confidence": 0.8}}

    out = run_goal_pipeline("I want to run a 5k next month",
                            goal_store=PostgresGoalStore(f, "u1"),
                            extractor_llm_fn=fake_llm, now=now)
    assert out.new_goals_created
    active = PostgresGoalStore(f, "u1").load_by_status(["active"])
    assert any(g.title == "run a 5k" for g in active)
