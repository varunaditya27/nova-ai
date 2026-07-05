import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory import state_updater
from backend.layer2_memory.schemas import (
    EpisodicMemory, EmotionVector, ScoredMemory, ShortTermMemoryBuffer,
)
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail

pytestmark = pytest.mark.docker


def test_reinforce_and_audit_roundtrip_live(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    f = make_session_factory(engine)
    store, audit = PostgresMemoryStore(f), PostgresAuditTrail(f, "itest")
    now = datetime.now(timezone.utc)
    mem = EpisodicMemory(user_id="itest", summary=f"live-{uuid4()}",
                         embedding=[0.1, 0.2], S_current=0.5, created_at=now)
    store.save_episodic(mem)
    scored = ScoredMemory(memory=mem, effective_score=0.9)
    stm = ShortTermMemoryBuffer(session_id="s1", user_id="itest")
    state_updater("itest", "s1", stm, store, audit, EmotionVector(), now,
                  lambda _s, _e: [], last_recall=[scored], used_memory_ids={mem.memory_id})
    assert store.get_episodic(mem.memory_id).S_current > 0.5
    assert audit.verify() is True
