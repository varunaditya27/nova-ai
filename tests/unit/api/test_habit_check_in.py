"""Habits are checked in from what the user says, with period-aware streaks, and show up on /goals."""
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.routes.goals import router
from backend.layer7_goals.engine import run_goal_pipeline
from backend.layer7_goals.schemas import Goal, Habit
from infra.db.engine import init_db, make_session_factory
from infra.db.goal_store import PostgresGoalStore

DAY1 = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)


def _sim(a, b):
    return 0.9 if "run" in a.lower() and "run" in b.lower() else 0.05


def _setup():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresGoalStore(factory, "local-user")
    store.add_goal(Goal(title="run a 5k", status="active", last_mentioned_at=DAY1, created_at=DAY1,
                        habits=[Habit(title="Go for a run", frequency="daily", status="active")]))
    return factory, store


def _habit(store):
    return store.load_by_status(["active"])[0].habits[0]


def _say(store, message, when):
    run_goal_pipeline(message, goal_store=store, similarity_fn=_sim, now=when)


def test_streak_builds_is_idempotent_per_day_and_resets_after_a_gap():
    _, store = _setup()
    _say(store, "I went for a run this morning", DAY1)
    _say(store, "went for another run this evening", DAY1 + timedelta(hours=9))   # same day
    assert (_habit(store).current_streak, _habit(store).total_check_ins) == (1, 1)
    _say(store, "I did my run again today", DAY1 + timedelta(days=1))
    assert _habit(store).current_streak == 2
    _say(store, "I went for a run", DAY1 + timedelta(days=4))                      # missed days
    assert (_habit(store).current_streak, _habit(store).best_streak) == (1, 2)


def test_unrelated_activity_is_not_a_check_in():
    _, store = _setup()
    _say(store, "I went to the dentist today", DAY1)
    assert _habit(store).total_check_ins == 0


def test_goals_route_exposes_habits_and_deadline():
    factory, store = _setup()
    _say(store, "I went for a run this morning", DAY1)
    app = FastAPI()
    app.state.nova = type("S", (), {"session_factory": factory, "default_user_id": "local-user"})()
    app.include_router(router)
    goal = TestClient(app).get("/goals").json()[0]
    assert goal["habits"] == [{"title": "Go for a run", "frequency": "daily", "current_streak": 1,
                               "best_streak": 1, "total_check_ins": 1}]
    assert goal["milestones"] == [] and goal["deadline"] is None
