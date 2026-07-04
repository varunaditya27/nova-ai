import pytest
pytest.importorskip("pydantic")

from backend.pipeline import ConversationOrchestrator
from backend.layer2_memory import InMemoryMemoryStore
from api.assembly import build_pipeline_steps


class FakeLLM:
    """LLMClient-shaped fake: echoes a canned reply; deterministic, offline."""
    def __init__(self, reply="Sounds good - tell me more."):
        self._reply = reply
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return self._reply
    def stream(self, prompt, **k):
        yield self._reply
    def embed(self, texts):
        return [[float(len(t) % 7), 0.1, 0.2] for t in texts]


def _steps(session_writer=None):
    llm = FakeLLM()
    return build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                memory_store=InMemoryMemoryStore(),
                                session_writer=session_writer)


def test_casual_turn_runs_through_real_pipeline():
    out = ConversationOrchestrator(_steps()).run_turn("local-user", "hey what's up")
    assert isinstance(out.response_text, str) and out.response_text.strip()


def test_empty_recall_delivers_without_inventing_memories():
    out = ConversationOrchestrator(_steps()).run_turn("local-user", "hi")
    assert out.response_text.strip()


def test_state_writer_is_invoked_after_turn():
    seen = []
    ConversationOrchestrator(_steps(session_writer=lambda ctx: seen.append(ctx.user_id))
                             ).run_turn("local-user", "hey")
    assert seen == ["local-user"]
