import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from datetime import datetime, timezone

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from api.state import build_app_state, make_episodic_writer


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
    return build_app_state(config={"system": {"default_user_id": "local-user"}, "llm": {}},
                           llm_clients=clients, engine=engine, vector_store=object())


class Ctx:
    user_id = "local-user"
    session_id = "s1"
    message = "hey there"
    now = datetime.now(timezone.utc)


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_episodic_writer_persists_memory_and_session():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    make_episodic_writer(store, FakeLLM(), factory)(Ctx())
    assert len(store.active_episodic("local-user")) == 1
    with session_scope(factory) as s:
        assert s.query(models.Session).filter_by(session_key="s1").one().turn_count == 1


def test_persisted_memory_survives_store_rebuild():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    make_episodic_writer(PostgresMemoryStore(factory), FakeLLM(), factory)(Ctx())
    # Fresh store object over the same database — simulates a process restart.
    rebuilt = PostgresMemoryStore(factory)
    recalled = rebuilt.active_episodic("local-user")
    assert len(recalled) == 1 and recalled[0].summary == "hey there"
    assert recalled[0].embedding == [0.1, 0.2, 0.3]
