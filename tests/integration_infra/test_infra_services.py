import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sqlalchemy")

from infra.vector_store import ChromaVectorStore
from infra.db import make_engine, make_session_factory, session_scope, init_db
import infra.db.models as models


@pytest.mark.docker
def test_ollama_complete_and_embed(ollama_url):
    ollama = pytest.importorskip("ollama")
    from infra.llm.ollama_client import OllamaClient

    # A reachable Ollama may still not have the models pulled (bare local daemon vs. the
    # dockerised service that pre-pulls them). Treat a missing model as a skip, not a failure.
    try:
        client = OllamaClient(model="qwen2.5:7b", base_url=ollama_url)
        text = client.complete("Say the word ready.")
        vecs = OllamaClient(model="nomic-embed-text", base_url=ollama_url).embed(["hello"])
    except ollama.ResponseError as exc:
        pytest.skip(f"required ollama model not pulled: {exc}")

    assert isinstance(text, str) and text
    assert len(vecs) == 1 and len(vecs[0]) > 0


@pytest.mark.docker
def test_chroma_add_query_delete(chroma_hostport):
    from infra.vector_store.collections import COLLECTIONS
    host, port = chroma_hostport
    store = ChromaVectorStore(host=host, port=port)
    # Hermetic: drop the shared collection so this test controls its embedding dimension regardless
    # of any prior real (768-dim nomic) or toy state left on the shared Chroma instance.
    try:
        store._client.delete_collection(COLLECTIONS["episodic"]["name"])
    except Exception:
        pass
    store.add("episodic", ids=["m1"], embeddings=[[0.1, 0.2, 0.3]],
              metadatas=[{"user_id": "u1"}], documents=["first"])
    hits = store.query("episodic", [0.1, 0.2, 0.3], n_results=1)
    assert hits and hits[0]["id"] == "m1"
    store.delete("episodic", ["m1"])
    store._client.delete_collection(COLLECTIONS["episodic"]["name"])  # leave no shared residue


@pytest.mark.docker
def test_postgres_model_crud(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.Goal(user_id="itest", goal_id="g-itest", status="active",
                          payload={"title": "ship infra"}))
    with session_scope(factory) as s:
        assert s.query(models.Goal).filter_by(user_id="itest").count() >= 1
        s.query(models.Goal).filter_by(user_id="itest").delete()
