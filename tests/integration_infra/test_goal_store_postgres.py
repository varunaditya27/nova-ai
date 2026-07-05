import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer7_goals import run_goal_pipeline
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.goal_store import PostgresGoalStore

pytestmark = pytest.mark.docker


def test_goal_pipeline_roundtrip_live(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    f = make_session_factory(engine)
    title = f"run-{uuid4()}"

    def fake_llm(_p):
        return {"goal_detected": True, "new_goal": {"inferred_title": title, "confidence": 0.9}}

    run_goal_pipeline("I want to " + title, goal_store=PostgresGoalStore(f, "itest"),
                      extractor_llm_fn=fake_llm, now=datetime.now(timezone.utc))
    assert any(g.title == title for g in PostgresGoalStore(f, "itest").load_by_status(["active"]))
