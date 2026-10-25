"""Recall surfaces memories relevant to *this* message — not the user's most important ones for any
message — while still allowing a near-exact emotional match when the user is distressed."""
import json
from datetime import datetime, timezone

from backend.layer2_memory import InMemoryMemoryStore
from backend.layer2_memory.schemas import EmotionVector, EpisodicMemory
from backend.pipeline import ConversationOrchestrator
from api.assembly import build_pipeline_steps


class LLM:
    """embed(): messages about exams point along axis 0, everything else along axis 1."""
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        if "Classify the message" in prompt:
            return json.dumps({"primary_label": "neutral", "valence": 0.1, "arousal": 0.3,
                               "confidence": 0.9, "crisis_flag": False, "primary_intent": "chitchat"})
        return "ok"
    def embed(self, texts):
        return [[1.0, 0.0] if "exam" in t.lower() else [0.0, 1.0] for t in texts]


def _orchestrator(user_id="u1"):
    store = InMemoryMemoryStore()
    store.save_episodic(EpisodicMemory(
        user_id=user_id, summary="User failed their exam", embedding=[1.0, 0.0],
        created_at=datetime.now(timezone.utc), importance_score=0.9, S_current=1.0, decay_rate=0.05,
        emotion_vector=EmotionVector(valence=0.1, arousal=0.3)))
    llm = LLM()
    return ConversationOrchestrator(build_pipeline_steps(
        system1=llm, system2=llm, embed=llm, memory_store=store))


def test_an_unrelated_message_recalls_nothing():
    out = _orchestrator().run_turn("u1", "what should I cook tonight")
    assert out.recalled_memories == [] and out.confabulation_guard


def test_a_related_message_recalls_the_memory():
    out = _orchestrator().run_turn("u1", "how do I prepare for my exam")
    assert [m.memory.summary for m in out.recalled_memories] == ["User failed their exam"]
