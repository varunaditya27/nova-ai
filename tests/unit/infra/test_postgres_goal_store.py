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


def test_get_is_user_scoped_no_cross_tenant_read():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    f = make_session_factory(engine)
    PostgresGoalStore(f, "u1").add_goal(Goal(goal_id="g1", title="a", status="active"))
    # A store bound to u2 must not read u1's goal by id.
    assert PostgresGoalStore(f, "u2").get("g1") is None
    assert PostgresGoalStore(f, "u1").get("g1").title == "a"


def test_get_relevant_goals_inherited():
    store = _store()
    now = datetime.now(timezone.utc)
    store.add_goal(Goal(goal_id="g1", title="run a 5k", status="active", last_mentioned_at=now))
    rel = store.get_relevant_goals("let's talk about the 5k", similarity_fn=lambda a, b: 1.0, now=now)
    assert rel and rel[0].goal.goal_id == "g1"


def test_signal_events_and_momentum_round_trip_through_postgres():
    from backend.layer7_goals.schemas import GoalSignalEvent

    store = _store()
    now = datetime.now(timezone.utc)
    goal = Goal(goal_id="g1", title="run 5k", status="active")
    goal.signal_events.append(GoalSignalEvent(
        goal_id="g1", event_type="progress_positive", timestamp=now, confidence=0.8))
    goal.momentum_score = 0.42
    store.add_goal(goal)

    reloaded = store.get("g1")
    assert len(reloaded.signal_events) == 1
    assert reloaded.signal_events[0].event_type == "progress_positive"
    assert isinstance(reloaded.signal_events[0].timestamp, datetime)  # not a raw string
    assert reloaded.momentum_score == 0.42

    from backend.layer7_goals.progress_monitor import compute_momentum
    assert compute_momentum(reloaded.signal_events, now=now) > 0.0


def test_signal_strength_round_trips_through_postgres():
    store = _store()
    store.add_goal(Goal(goal_id="g1", title="run 5k", status="active",
                        signal_strength="implicit_aspired"))
    assert store.get("g1").signal_strength == "implicit_aspired"
