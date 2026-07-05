import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory.schemas import EpisodicMemory, UserWorldModel, PersonNode
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore

pytestmark = pytest.mark.docker


def test_episodic_roundtrip_against_live_postgres(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    store = PostgresMemoryStore(make_session_factory(engine))
    uid = f"itest-{uuid4()}"
    text = "persisted through real JSONB"
    store.save_episodic(EpisodicMemory(
        user_id=uid, summary=text, embedding=[0.1, 0.2, 0.3],
        created_at=datetime.now(timezone.utc), S_current=0.9))
    got = store.active_episodic(uid)
    assert len(got) == 1 and got[0].summary == text and got[0].S_current == 0.9


def test_uwm_roundtrip_against_live_postgres(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    store = PostgresMemoryStore(make_session_factory(engine))
    uid = uuid4()
    uwm = UserWorldModel(user_id=uid)
    uwm.relationship_graph.people.append(PersonNode(name="Alex"))
    store.save_uwm(uwm)
    loaded = store.load_uwm(str(uid))
    assert loaded.relationship_graph.people[0].name == "Alex"
