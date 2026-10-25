"""Goal progress signals only apply to a goal the message is actually about — "I'm done for the
day" must never complete the user's running goal just because it was mentioned recently."""
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.layer7_goals.engine import run_goal_pipeline
from backend.layer7_goals.schemas import Goal
from infra.db.engine import init_db, make_session_factory
from infra.db.goal_store import PostgresGoalStore

NOW = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)


def _store():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    store = PostgresGoalStore(make_session_factory(engine), "u1")
    store.add_goal(Goal(title="run a 5k", status="active", last_mentioned_at=NOW,
                        created_at=NOW, emotional_weight=0.5))
    return store


def _status(store):
    return store.load_by_status(["active", "completed", "abandoned"])[0].status


def _topical(a, b):
    return 0.9 if "5k" in a.lower() or "run" in a.lower() else 0.05


def test_unrelated_chatter_never_completes_or_abandons_a_goal():
    store = _store()
    for message in ("I'm done for the day, so tired", "I made it home finally",
                    "forget it, never mind", "I finished my coffee and I'm lost",
                    "not worth it, I'm giving up coffee"):
        run_goal_pipeline(message, goal_store=store, similarity_fn=_topical, now=NOW)
    assert _status(store) == "active"


def test_a_real_completion_statement_about_the_goal_still_completes_it():
    store = _store()
    run_goal_pipeline("I finally did it, I ran my first 5k!", goal_store=store,
                      similarity_fn=_topical, now=NOW)
    assert _status(store) == "completed"
