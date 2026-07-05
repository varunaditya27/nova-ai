import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from api.state import build_app_state, make_session_writer


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


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_session_writer_persists_turn_row():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    writer = make_session_writer(factory)

    class Ctx:
        user_id = "local-user"; session_id = "s1"; message = "hey"; response_text = "hi"
    writer(Ctx())
    with session_scope(factory) as s:
        assert s.query(models.EpisodicMemory).filter_by(user_id="local-user").count() == 1
        assert s.query(models.Session).filter_by(session_key="s1").one().turn_count == 1
