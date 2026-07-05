import asyncio
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer2_memory import memory_arbiter, DeterministicEmbedder
from backend.layer2_memory.schemas import ConversationMode, EmotionVector, EpisodicMemory
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore


def _store():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresMemoryStore(make_session_factory(engine))


def test_arbiter_recalls_a_persisted_memory():
    emb = DeterministicEmbedder()
    store = _store()
    text = "user loves hiking in the mountains every weekend"
    store.save_episodic(EpisodicMemory(
        user_id="u1", summary=text, embedding=emb.embed(text),
        created_at=datetime.now(timezone.utc), S_current=1.0, importance_score=0.6))
    packet = asyncio.run(memory_arbiter(
        "u1", "tell me about hiking", EmotionVector(), ConversationMode.CASUAL,
        datetime.now(timezone.utc), store=store, embedder=emb))
    assert packet.recalled_memories
    assert not packet.confabulation_guard


def test_arbiter_empty_store_sets_confabulation_guard():
    packet = asyncio.run(memory_arbiter(
        "u1", "hi", EmotionVector(), ConversationMode.CASUAL, datetime.now(timezone.utc),
        store=_store(), embedder=DeterministicEmbedder()))
    assert packet.confabulation_guard
    assert packet.cold_start
