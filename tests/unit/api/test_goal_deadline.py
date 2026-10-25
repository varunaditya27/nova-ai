"""A deadline the user states reaches Goal.deadline, so goal check-ins and the longitudinal
"upcoming deadlines" brief have something real to work from."""
import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.layer7_goals.engine import run_goal_pipeline
from infra.db.engine import init_db, make_session_factory
from infra.db.goal_store import PostgresGoalStore

NOW = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)


def _store():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    return PostgresGoalStore(make_session_factory(engine), "u1")


def _run(store, deadline_date):
    seen = {}

    def llm(prompt):
        seen["prompt"] = prompt
        return json.dumps({"goal_detected": True, "new_goal": {
            "inferred_title": "finish my DSA course", "confidence": 0.9,
            "has_explicit_deadline": True, "deadline_description": "by December",
            "deadline_date": deadline_date}})

    run_goal_pipeline("I want to finish my DSA course by December", goal_store=store,
                      extractor_llm_fn=llm, now=NOW)
    return seen["prompt"], store.load_by_status(["active"])[0]


def test_stated_deadline_populates_the_goal_and_the_model_is_told_todays_date():
    prompt, goal = _run(_store(), "2026-12-31")
    assert "Today's date is 2026-10-25" in prompt
    assert goal.deadline.date().isoformat() == "2026-12-31"


def test_a_past_or_garbled_date_is_dropped():
    assert _run(_store(), "2024-12-31")[1].deadline is None
    assert _run(_store(), "december-ish")[1].deadline is None
