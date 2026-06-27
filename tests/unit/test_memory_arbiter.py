"""Tests for the Memory Arbiter orchestration + MemoryPacket (architecture doc §11, §15)."""

import asyncio
from datetime import datetime
from uuid import uuid4

from backend.layer2_memory import arbiter as arb
from backend.layer2_memory.embedding import DeterministicEmbedder
from backend.layer2_memory.memory_store import InMemoryMemoryStore
from backend.layer2_memory.schemas import (
    CommunicationModel,
    ConversationMode,
    EmotionVector,
    EpisodicMemory,
    MemoryPacket,
    SemanticMemory,
    Stressor,
    LifeContext,
    UserWorldModel,
)

NOW = datetime(2026, 6, 26, 12, 0, 0)
EMB = DeterministicEmbedder(dim=64)


def _run(coro):
    return asyncio.run(coro)


def _episode(user, text, **kw):
    base = dict(user_id=user, summary=text, embedding=EMB.embed(text), created_at=NOW,
                emotion_vector=EmotionVector(valence=-0.5, arousal=0.7), emotional_weight=0.8,
                importance_score=0.8, S_current=0.9, decay_rate=0.02)
    base.update(kw)
    return EpisodicMemory(**base)


def test_cold_start_empty_store_sets_confabulation_guard():
    store = InMemoryMemoryStore()
    packet = _run(arb.memory_arbiter(
        user_id=uuid4(), query_text="how are things", current_emotion=EmotionVector(),
        conversation_mode=ConversationMode.CASUAL, now=NOW, store=store, embedder=EMB,
    ))
    assert isinstance(packet, MemoryPacket)
    assert packet.recalled_memories == []
    assert packet.no_relevant_memories is True
    assert packet.confabulation_guard is True
    assert packet.cold_start is True


def test_recall_returns_scored_memories_capped_at_three():
    user = uuid4()
    store = InMemoryMemoryStore()
    for i in range(5):
        store.save_episodic(_episode(user, "placement interview anxiety"))
    packet = _run(arb.memory_arbiter(
        user_id=user, query_text="placement interview anxiety",
        current_emotion=EmotionVector(valence=-0.5, arousal=0.7),
        conversation_mode=ConversationMode.EMOTIONAL_SUPPORT, now=NOW, store=store, embedder=EMB,
    ))
    assert len(packet.recalled_memories) == 3
    assert packet.confabulation_guard is False
    top = packet.recalled_memories[0]
    assert set(top.components) == {"semantic", "emotional", "temporal", "importance"}
    assert top.effective_score > 0


def test_context_gate_demotes_emotional_episodic_in_casual_mode():
    user = uuid4()
    store = InMemoryMemoryStore()
    emotional = _episode(user, "placement interview anxiety")           # emotional episodic
    semantic = SemanticMemory(user_id=user, statement="placement interview anxiety",
                              embedding=EMB.embed("placement interview anxiety"),
                              confidence=0.8, S_current=1.0, last_confirmed_at=NOW)
    store.save_episodic(emotional)
    store.save_semantic(semantic)
    packet = _run(arb.memory_arbiter(
        user_id=user, query_text="placement interview anxiety",
        current_emotion=EmotionVector(valence=-0.5, arousal=0.7),
        conversation_mode=ConversationMode.CASUAL, now=NOW, store=store, embedder=EMB,
    ))
    # In casual mode the emotional episodic gate is 0.10 vs semantic 0.50 → semantic wins.
    assert isinstance(packet.recalled_memories[0].memory, SemanticMemory)


def test_uwm_context_populated_when_present():
    user = uuid4()
    store = InMemoryMemoryStore()
    store.save_episodic(_episode(user, "placement anxiety"))
    store.save_uwm(UserWorldModel(
        user_id=user,
        life_context=LifeContext(active_stressors=[Stressor(description="placements")]),
        communication_model=CommunicationModel(prefers_direct_answers=True),
    ))
    packet = _run(arb.memory_arbiter(
        user_id=user, query_text="placement anxiety", current_emotion=EmotionVector(),
        conversation_mode=ConversationMode.EMOTIONAL_SUPPORT, now=NOW, store=store, embedder=EMB,
    ))
    assert packet.uwm_unavailable is False
    assert packet.uwm_context.active_stressors[0].description == "placements"
    assert packet.uwm_context.communication_preferences.prefers_direct_answers is True


def test_uwm_unavailable_flag_when_no_uwm():
    user = uuid4()
    store = InMemoryMemoryStore()
    store.save_episodic(_episode(user, "placement anxiety"))
    packet = _run(arb.memory_arbiter(
        user_id=user, query_text="placement anxiety", current_emotion=EmotionVector(),
        conversation_mode=ConversationMode.EMOTIONAL_SUPPORT, now=NOW, store=store, embedder=EMB,
    ))
    assert packet.uwm_unavailable is True


def test_store_failure_degrades_gracefully():
    class ExplodingStore(InMemoryMemoryStore):
        def candidate_memories(self, user_id):
            raise RuntimeError("vector store down")

    packet = _run(arb.memory_arbiter(
        user_id=uuid4(), query_text="x", current_emotion=EmotionVector(),
        conversation_mode=ConversationMode.CASUAL, now=NOW, store=ExplodingStore(), embedder=EMB,
    ))
    assert isinstance(packet, MemoryPacket)
    assert packet.recall_degraded is True
    assert packet.recalled_memories == []
    assert packet.confabulation_guard is True
