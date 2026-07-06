"""Goal accountability + relationship familiarity are injected into the planner prompt."""
import pytest
pytest.importorskip("pydantic")

from backend.pipeline import ConversationOrchestrator
from backend.layer2_memory import InMemoryMemoryStore
from backend.layer4_persona.schemas import RelationshipState
from api.assembly import build_pipeline_steps


class CapturingLLM:
    """Records every prompt the planner builds so we can assert on injected directives."""
    def __init__(self):
        self.prompts = []
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        self.prompts.append(prompt)
        return "Sounds good."
    def stream(self, prompt, **k):
        yield "Sounds good."
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _steps(llm, goal_provider=None, relationship_provider=None):
    return build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                memory_store=InMemoryMemoryStore(),
                                goal_provider=goal_provider,
                                relationship_provider=relationship_provider)


def test_goal_titles_injected_into_prompt():
    llm = CapturingLLM()
    steps = _steps(llm, goal_provider=lambda uid, msg: ["run a 5k", "learn guitar"])
    ConversationOrchestrator(steps).run_turn("u1", "how's my week going?")
    assert any("run a 5k" in p for p in llm.prompts)


def test_relationship_stage_injected_into_prompt():
    llm = CapturingLLM()
    rel = RelationshipState(stage="developing", total_messages_exchanged=120, total_sessions=20)
    steps = _steps(llm, relationship_provider=lambda uid: rel)
    ConversationOrchestrator(steps).run_turn("u1", "hey")
    assert any("developing" in p for p in llm.prompts)


def test_no_providers_still_generates():
    llm = CapturingLLM()
    out = ConversationOrchestrator(_steps(llm)).run_turn("u1", "hi")
    assert out.response_text.strip()
