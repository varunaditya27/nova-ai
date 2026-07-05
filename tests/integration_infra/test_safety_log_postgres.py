import pytest
pytest.importorskip("sqlalchemy")

from uuid import uuid4

from backend.layer11_safety.schemas import CrisisSignal
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.safety_store import PostgresSafetyLog

pytestmark = pytest.mark.docker


def test_safety_log_roundtrip_live(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    log = PostgresSafetyLog(make_session_factory(engine))
    uid = f"itest-{uuid4()}"
    log.record(CrisisSignal(user_id=uid, tier="tier_2", confidence=0.6))
    recent = log.recent(uid)
    assert len(recent) == 1 and recent[0].tier == "tier_2" and recent[0].confidence == 0.6
