import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer2_memory import state_updater
from backend.layer2_memory.schemas import (
    EpisodicMemory, EmotionVector, ScoredMemory, ShortTermMemoryBuffer,
)
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail


def _ctx():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    f = make_session_factory(engine)
    return PostgresMemoryStore(f), PostgresAuditTrail(f, "u1")


def _no_new_episodes(_stm, _emotion):
    return []


def test_reinforced_memory_strength_persists():
    store, audit = _ctx()
    now = datetime.now(timezone.utc)
    mem = EpisodicMemory(user_id="u1", summary="loves hiking",
                         embedding=[0.1, 0.2], S_current=0.5, importance_score=0.6,
                         created_at=now)
    store.save_episodic(mem)
    scored = ScoredMemory(memory=mem, effective_score=0.9)
    stm = ShortTermMemoryBuffer(session_id="s1", user_id="u1")
    state_updater("u1", "s1", stm, store, audit, EmotionVector(), now, _no_new_episodes,
                  last_recall=[scored], used_memory_ids={mem.memory_id})
    reloaded = store.get_episodic(mem.memory_id)
    assert reloaded.S_current > 0.5           # reinforced AND persisted through the store
    assert reloaded.reinforcement_count == 1
    assert audit.verify() is True
