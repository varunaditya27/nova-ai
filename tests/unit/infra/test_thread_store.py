import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timedelta, timezone

from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.thread_store import PostgresThreadStore
from backend.layer1_input.schemas import (
    ImportanceTier, NarrativeThread, ThreadStatus, ThreadType,
)
from backend.layer1_input import thread_tracker

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def _store(user="u1"):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresThreadStore(make_session_factory(engine), user)


def _thread(thread_id, due_offset_hours, **kw):
    import uuid
    return NarrativeThread(
        thread_id=uuid.uuid5(uuid.NAMESPACE_URL, thread_id),
        summary=kw.pop("summary", "a pending thing"),
        created_at=NOW, follow_up_due_at=NOW + timedelta(hours=due_offset_hours),
        status=kw.pop("status", ThreadStatus.UNRESOLVED),
        importance_tier=kw.pop("importance_tier", ImportanceTier.MEDIUM),
        thread_type=kw.pop("thread_type", ThreadType.FACTUAL_PENDING),
        **kw)


def test_save_and_get_all_round_trips_through_the_real_store():
    store = _store()
    store.save(_thread("t1", -2, summary="had a job interview"))
    threads = store.get_all()
    assert len(threads) == 1
    assert threads[0].summary == "had a job interview"
    assert threads[0].status == ThreadStatus.UNRESOLVED
    assert threads[0].thread_type == ThreadType.FACTUAL_PENDING


def test_save_upserts_on_the_same_thread_id():
    store = _store()
    thread = _thread("t1", -2)
    store.save(thread)
    thread.status = ThreadStatus.RESOLVED
    store.save(thread)
    assert len(store.get_all()) == 1
    assert store.get_all()[0].status == ThreadStatus.RESOLVED


def test_get_all_filters_by_status():
    store = _store()
    store.save(_thread("t1", -2, status=ThreadStatus.UNRESOLVED))
    store.save(_thread("t2", -2, status=ThreadStatus.RESOLVED))
    assert len(store.get_all(status=ThreadStatus.UNRESOLVED)) == 1
    assert len(store.get_all(status=ThreadStatus.RESOLVED)) == 1


def test_mark_status_updates_a_persisted_thread():
    store = _store()
    thread = _thread("t1", -2)
    store.save(thread)
    store.mark_status(thread.thread_id, ThreadStatus.RESOLVED)
    assert store.get_all()[0].status == ThreadStatus.RESOLVED


def test_is_user_scoped():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    from infra.db.engine import make_session_factory as msf
    f = msf(engine)
    PostgresThreadStore(f, "u1").save(_thread("t1", -2))
    assert PostgresThreadStore(f, "u2").get_all() == []


def test_real_store_feeds_thread_trackers_due_candidates():
    """Proves the store satisfies the real ThreadStore Protocol end-to-end -- due_candidates
    (thread_tracker.py) is Layer 1's actual consumer of get_all(), not a mock."""
    store = _store()
    store.save(_thread("overdue", -5, summary="overdue thing", emotional_weight=0.9,
                       importance_tier=ImportanceTier.HIGH))
    store.save(_thread("future", 5, summary="not due yet"))
    due = thread_tracker.due_candidates(store, NOW)
    assert len(due) == 1 and due[0].summary == "overdue thing"
