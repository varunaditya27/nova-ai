"""STM turns and narrative chains reach the planner prompt through the real orchestrator."""
import json
from datetime import datetime, timezone

import pytest
pytest.importorskip("pydantic")

from backend.pipeline import ConversationOrchestrator
from backend.layer2_memory.schemas import ChainedEpisode, NarrativeChain, NarrativeLinkType
from api.assembly import build_pipeline_steps
from api.session_context import make_session_context_provider
from api.state import make_state_update_writer
from infra.db import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from infra.stm_store import InProcessSTMStore


class CapturingLLM:
    def __init__(self):
        self.prompts = []
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        if "Classify the message" in prompt:
            return json.dumps({"primary_label": "neutral", "valence": 0.1, "arousal": 0.3,
                               "confidence": 0.9, "crisis_flag": False, "primary_intent": "chitchat"})
        self.prompts.append(prompt)
        return "Noted."
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _orchestrator(llm, with_chain=False):
    factory = make_session_factory(_engine := make_engine("sqlite+pysqlite:///:memory:"))
    init_db(_engine)
    store, stm = PostgresMemoryStore(factory), InProcessSTMStore()
    if with_chain:
        now = datetime.now(timezone.utc)
        ep = lambda i: ChainedEpisode(episode_id=f"e{i}", position_in_chain=i,
                                      link_type=NarrativeLinkType.CONTINUATION, linked_at=now)
        store.save_narrative_chain("u1", NarrativeChain(
            theme="job hunt after the layoff", episodes=[ep(0), ep(1)],
            first_episode_at=now, last_episode_at=now))
    steps = build_pipeline_steps(
        system1=llm, system2=llm, embed=llm, memory_store=store,
        session_writer=make_state_update_writer(store, llm, factory, 0.5, stm_store=stm),
        session_context_provider=make_session_context_provider(stm, store))
    return ConversationOrchestrator(steps)


def test_earlier_turn_in_same_session_reaches_prompt():
    llm = CapturingLLM()
    orch = _orchestrator(llm)
    orch.run_turn("u1", "my cat Biscuit is named after a cookie", session_id="s1")
    llm.prompts.clear()
    orch.run_turn("u1", "what was that about?", session_id="s1")
    assert any("Biscuit" in p for p in llm.prompts)


def test_other_session_is_not_leaked():
    llm = CapturingLLM()
    orch = _orchestrator(llm)
    orch.run_turn("u1", "my cat Biscuit", session_id="s1")
    llm.prompts.clear()
    orch.run_turn("u1", "hello", session_id="s2")
    assert not any("Biscuit" in p for p in llm.prompts)


def test_multi_episode_chain_theme_reaches_prompt():
    llm = CapturingLLM()
    _orchestrator(llm, with_chain=True).run_turn("u1", "hello there", session_id="s1")
    assert any("job hunt after the layoff" in p for p in llm.prompts)
