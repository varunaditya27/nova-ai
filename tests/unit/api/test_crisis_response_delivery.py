"""A confirmed crisis delivers SC-3's regional protocol (real helplines), not the generic fallback."""
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.state import build_app_state
from infra.db.engine import init_db


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "ok"
    def stream(self, prompt, **k):
        yield "ok"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _state():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    return build_app_state(
        config={"system": {"default_user_id": "u1"}, "llm": {}, "memory": {}},
        llm_clients=clients, engine=engine, vector_store=object())


def test_tier_1_delivers_regional_helplines_and_a_safety_check():
    out = _state().orchestrator.run_turn("u1", "I want to kill myself", session_id="s1")
    assert out.crisis_active
    assert "Vandrevala" in out.response_text and "iCall" in out.response_text
    assert "safe right now" in out.response_text


def test_tier_2_delivers_helplines_too():
    out = _state().orchestrator.run_turn("u1", "I don't want to be here anymore", session_id="s1")
    assert out.crisis_active and "Vandrevala" in out.response_text
