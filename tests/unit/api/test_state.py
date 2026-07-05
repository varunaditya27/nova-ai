import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from datetime import datetime, timezone

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail
from backend.layer2_memory.schemas import EpisodicMemory, ScoredMemory
from api.state import build_app_state, make_state_update_writer


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "hi there"
    def stream(self, prompt, **k):
        yield "hi there"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _sqlite_state():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    return build_app_state(config={"system": {"default_user_id": "local-user"},
                                   "llm": {}, "memory": {}},
                           llm_clients=clients, engine=engine, vector_store=object())


class Ctx:
    user_id = "local-user"
    session_id = "s1"
    message = "hey there"
    now = datetime.now(timezone.utc)
    response_text = "loves hiking"
    emotion_intent = None
    recalled_memories = []


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_writer_persists_episode_session_and_audit():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1)(Ctx())
    assert any(m.summary == "hey there" for m in store.active_episodic("local-user"))
    with session_scope(factory) as s:
        assert s.query(models.Session).filter_by(session_key="s1").one().turn_count == 1
    assert PostgresAuditTrail(factory, "local-user").verify() is True


def test_writer_reinforces_similarity_matched_recalled_memory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="loves hiking",
                         embedding=[0.1, 0.2, 0.3], S_current=0.5,
                         created_at=datetime.now(timezone.utc))
    store.save_episodic(mem)

    class C(Ctx):
        recalled_memories = [ScoredMemory(memory=mem, effective_score=0.9)]
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1)(C())
    assert store.get_episodic(mem.memory_id).S_current > 0.5
