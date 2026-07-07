import pytest
pytest.importorskip("sqlalchemy")

from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.onboarding_store import PostgresOnboardingStore


def _factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def test_new_user_defaults_to_active():
    st = PostgresOnboardingStore(_factory(), "u1").state()
    assert st["cold_start_active"] is True and st["session_index"] == 0


def test_distinct_sessions_increment_once_each():
    f = _factory()
    store = PostgresOnboardingStore(f, "u1", graduation_sessions=5)
    store.record_turn("s1")
    store.record_turn("s1")  # same session — not double-counted
    store.record_turn("s2")
    assert PostgresOnboardingStore(f, "u1").state()["session_index"] == 2


def test_graduation_flips_flag_at_threshold():
    f = _factory()
    store = PostgresOnboardingStore(f, "u1", graduation_sessions=2)
    store.record_turn("s1")
    assert PostgresOnboardingStore(f, "u1").state()["cold_start_active"] is True
    store.record_turn("s2")
    assert PostgresOnboardingStore(f, "u1").state()["cold_start_active"] is False


def test_user_scoped():
    f = _factory()
    PostgresOnboardingStore(f, "u1").record_turn("s1")
    assert PostgresOnboardingStore(f, "u2").state()["session_index"] == 0


def test_elicitation_state_and_record():
    f = _factory()
    store = PostgresOnboardingStore(f, "u1", graduation_sessions=5)
    assert store.elicitation_state("s1") == {"surfaced_targets": [], "asked_this_session": False}
    store.record_elicitation("s1", "user_handle")
    st = store.elicitation_state("s1")
    assert st["surfaced_targets"] == ["user_handle"] and st["asked_this_session"] is True
    # a different session has not asked yet, but the surfaced target persists (never re-asked)
    st2 = store.elicitation_state("s2")
    assert st2["surfaced_targets"] == ["user_handle"] and st2["asked_this_session"] is False


def test_record_elicitation_does_not_reset_graduation_counter():
    f = _factory()
    store = PostgresOnboardingStore(f, "u1", graduation_sessions=5)
    store.record_turn("s1")
    store.record_elicitation("s1", "life_phase")
    assert PostgresOnboardingStore(f, "u1").state()["session_index"] == 1
