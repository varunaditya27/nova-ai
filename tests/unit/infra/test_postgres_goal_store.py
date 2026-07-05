import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer7_goals.schemas import Goal
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.goal_store import PostgresGoalStore


def _store(user="u1"):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresGoalStore(make_session_factory(engine), user)


def test_add_get_and_status_filter():
    store = _store()
    store.add_goal(Goal(goal_id="g1", title="run 5k", status="active"))
    store.add_goal(Goal(goal_id="g2", title="read more", status="paused"))
    assert store.get("g1").title == "run 5k"
    assert [g.goal_id for g in store.load_by_status(["active"])] == ["g1"]


def test_goal_id_upsert_and_update():
    store = _store()
    store.add_goal(Goal(goal_id="g1", title="v1", status="active"))
    store.update_goal(Goal(goal_id="g1", title="v2", status="active"))
    active = store.load_by_status(["active"])
    assert len(active) == 1 and active[0].title == "v2"


def test_cross_user_isolation():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    f = make_session_factory(engine)
    PostgresGoalStore(f, "u1").add_goal(Goal(goal_id="g1", title="a", status="active"))
    PostgresGoalStore(f, "u2").add_goal(Goal(goal_id="g2", title="b", status="active"))
    assert [g.title for g in PostgresGoalStore(f, "u1").load_by_status(["active"])] == ["a"]


def test_get_relevant_goals_inherited():
    store = _store()
    now = datetime.now(timezone.utc)
    store.add_goal(Goal(goal_id="g1", title="run a 5k", status="active", last_mentioned_at=now))
    rel = store.get_relevant_goals("let's talk about the 5k", similarity_fn=lambda a, b: 1.0, now=now)
    assert rel and rel[0].goal.goal_id == "g1"
