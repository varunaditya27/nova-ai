import pytest
pytest.importorskip("sqlalchemy")

from backend.layer11_safety.schemas import CrisisSignal, CrisisTier
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.safety_store import PostgresSafetyLog


def _log():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresSafetyLog(make_session_factory(engine))


def test_record_and_recent_most_recent_first():
    log = _log()
    log.record(CrisisSignal(user_id="u1", tier=CrisisTier.TIER_3.value, confidence=0.3))
    log.record(CrisisSignal(user_id="u1", tier=CrisisTier.TIER_2.value, confidence=0.6))
    recent = log.recent("u1")
    assert [s.tier for s in recent] == [CrisisTier.TIER_2.value, CrisisTier.TIER_3.value]
    assert recent[0].confidence == 0.6


def test_recent_is_user_scoped():
    log = _log()
    log.record(CrisisSignal(user_id="u1", tier="tier_2"))
    log.record(CrisisSignal(user_id="u2", tier="tier_1"))
    assert [s.tier for s in log.recent("u1")] == ["tier_2"]
