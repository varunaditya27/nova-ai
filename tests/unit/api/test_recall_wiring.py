"""Recall now matches the write path's raw user_id, and uses ANN when a vector store is present."""
import pytest
pytest.importorskip("pydantic")
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from backend.layer2_memory.schemas import EpisodicMemory
from api.assembly import build_pipeline_steps


class LLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "ok"
    def stream(self, prompt, **k):
        yield "ok"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVS:
    """Records adds and returns everything indexed under the queried user as ANN hits."""
    def __init__(self):
        self.rows = []
    def add(self, collection, ids, embeddings, metadatas=None, documents=None):
        for i, mid in enumerate(ids):
            self.rows.append((mid, (metadatas or [{}])[i].get("user_id")))
    def query(self, collection, embedding, n_results=3, where=None):
        uid = (where or {}).get("user_id")
        return [{"id": mid} for mid, u in self.rows if u == uid][:n_results]
    def delete(self, collection, ids):
        self.rows = [(m, u) for (m, u) in self.rows if m not in set(ids)]


def _seed(factory, uid="u1"):
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id=uid, summary="I love hiking in the alps",
                         embedding=[0.1, 0.2, 0.3], S_current=1.0, importance_score=0.5,
                         created_at=datetime.now(timezone.utc))
    store.save_episodic(mem)
    return store, mem


class _Packet:
    def __init__(self, msg):
        self.raw_message = msg


def _factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def test_recall_matches_raw_user_id_linear_path():
    factory = _factory()
    store, mem = _seed(factory, "u1")
    steps = build_pipeline_steps(system1=LLM(), system2=LLM(), embed=LLM(), memory_store=store)
    recalled = steps.recall("u1", _Packet("tell me about hiking"))
    # Previously the recall passed uuid5(user_id) and matched nothing; now it finds the episode.
    assert any("hiking" in getattr(getattr(r, "memory", r), "summary", "") for r in recalled)


def test_recall_uses_ann_when_vector_store_present():
    factory = _factory()
    store, mem = _seed(factory, "u1")
    vs = FakeVS()
    vs.add("episodic", ids=[str(mem.memory_id)], embeddings=[[0.1, 0.2, 0.3]],
           metadatas=[{"user_id": "u1"}], documents=["I love hiking in the alps"])
    steps = build_pipeline_steps(system1=LLM(), system2=LLM(), embed=LLM(),
                                 memory_store=store, vector_store=vs)
    recalled = steps.recall("u1", _Packet("tell me about hiking"))
    assert any("hiking" in getattr(getattr(r, "memory", r), "summary", "") for r in recalled)
