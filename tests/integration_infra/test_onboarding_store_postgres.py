import pytest
pytest.importorskip("sqlalchemy")

from uuid import uuid4

from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.onboarding_store import PostgresOnboardingStore

pytestmark = pytest.mark.docker


def test_onboarding_roundtrip_live(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    f = make_session_factory(engine)
    uid = f"itest-{uuid4()}"
    PostgresOnboardingStore(f, uid, graduation_sessions=2).record_turn("s1")
    PostgresOnboardingStore(f, uid, graduation_sessions=2).record_turn("s2")
    st = PostgresOnboardingStore(f, uid).state()
    assert st["session_index"] == 2 and st["cold_start_active"] is False
