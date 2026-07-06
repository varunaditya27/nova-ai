import pytest
pytest.importorskip("sqlalchemy")

from datetime import date

from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.proactive_store import PostgresProactiveQueue
from infra.db.longitudinal_store import PostgresLongitudinalStore
from backend.layer6_proactivity.schemas import ProactiveItem
from backend.layer10_longitudinal.schemas import WeeklySummary


def _factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def _summary(summary_id, narrative=""):
    return WeeklySummary(user_id="u1", week_start_date=date(2026, 7, 1),
                         week_end_date=date(2026, 7, 7), summary_id=summary_id,
                         week_narrative=narrative)


# ── Layer 6 proactive queue ──────────────────────────────────────────────────
def test_proactive_upsert_and_load_roundtrip():
    q = PostgresProactiveQueue(_factory(), "u1")
    item = ProactiveItem(item_id="p1", item_type="goal_check_in", status="pending",
                         content_basis="your 5k goal")
    q.upsert(item)
    loaded = q.load()
    assert len(loaded) == 1 and loaded[0].item_id == "p1"
    assert loaded[0].content_basis == "your 5k goal"


def test_proactive_upsert_updates_status_and_filters():
    f = _factory()
    q = PostgresProactiveQueue(f, "u1")
    q.upsert(ProactiveItem(item_id="p1", item_type="goal_check_in", status="pending"))
    q.upsert(ProactiveItem(item_id="p2", item_type="silence_break", status="expired"))
    assert {i.item_id for i in q.load(statuses=["pending"])} == {"p1"}
    # Re-upsert p1 with a new status → same row, updated.
    q.upsert(ProactiveItem(item_id="p1", item_type="goal_check_in", status="delivered"))
    assert q.load(statuses=["pending"]) == []
    assert {i.item_id for i in q.load(statuses=["delivered"])} == {"p1"}


def test_proactive_is_user_scoped():
    f = _factory()
    PostgresProactiveQueue(f, "u1").upsert(ProactiveItem(item_id="p1", status="pending"))
    assert PostgresProactiveQueue(f, "u2").load() == []


# ── Layer 10 longitudinal ────────────────────────────────────────────────────
def test_longitudinal_save_and_latest():
    store = PostgresLongitudinalStore(_factory(), "u1")
    store.save_summary(_summary("w1", "a good week"))
    store.save_summary(_summary("w2", "an even better week"))
    assert store.latest().summary_id == "w2"
    assert len(store.summaries()) == 2
    assert store.latest().week_narrative == "an even better week"
    # date fields survive the JSONB round-trip.
    assert store.latest().week_start_date == date(2026, 7, 1)


def test_longitudinal_is_user_scoped():
    f = _factory()
    PostgresLongitudinalStore(f, "u1").save_summary(_summary("w1"))
    assert PostgresLongitudinalStore(f, "u2").summaries() == []
