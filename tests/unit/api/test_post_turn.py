"""Post-turn writers run off the response path, but the next turn always reads their results."""
import threading
import time

from api.post_turn import PostTurnRunner
from api.state import build_app_state
from infra.db import make_engine, init_db
from infra.db.message_store import PostgresMessageStore


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "hi there"
    def stream(self, prompt, **k):
        yield "hi there"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_runner_inline_when_not_background():
    seen = []
    runner = PostTurnRunner(seen.append, background=False)
    runner.submit("t1")
    assert seen == ["t1"]


def test_runner_defers_until_drained_and_survives_a_failing_writer():
    done = threading.Event()

    def slow(_ctx):
        time.sleep(0.2)
        done.set()
        raise RuntimeError("writer blew up")

    runner = PostTurnRunner(slow, background=True)
    runner.submit("t1")
    assert not done.is_set()          # submit returned before the writer finished
    runner.drain()                    # drain waits, and a writer failure never propagates
    assert done.is_set()
    runner.shutdown()


def test_real_turn_returns_before_deferred_writes_and_next_turn_sees_them(tmp_path):
    engine = make_engine(f"sqlite+pysqlite:///{tmp_path / 'n.db'}")
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    state = build_app_state(
        config={"system": {"default_user_id": "u1", "post_turn_background": True},
                "llm": {}, "memory": {}},
        llm_clients=clients, engine=engine, vector_store=object())
    finished = []
    real_writer = state.post_turn._writer

    def slow_writer(ctx):
        time.sleep(0.3)
        real_writer(ctx)
        finished.append(ctx.message)

    state.post_turn._writer = slow_writer
    state.orchestrator.run_turn("u1", "first message", session_id="s1")
    assert finished == []                                   # response was not held up by the writers
    assert len(_messages(state)) == 2                       # the message log is already durable
    state.orchestrator.run_turn("u1", "second message", session_id="s1")
    assert finished == ["first message"]                    # turn 2 drained turn 1 before reading
    state.post_turn.shutdown()
    assert finished == ["first message", "second message"]


def _messages(state):
    return PostgresMessageStore(state.session_factory, "u1").history(limit=50)
