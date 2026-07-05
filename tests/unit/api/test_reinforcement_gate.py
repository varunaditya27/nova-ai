from backend.layer2_memory import DeterministicEmbedder
from backend.layer2_memory.schemas import EpisodicMemory, ScoredMemory
from api.reinforcement import used_memory_ids


def test_gate_includes_reflected_excludes_unreflected():
    emb = DeterministicEmbedder()
    hiking = EpisodicMemory(user_id="u1", summary="loves hiking in the mountains",
                            embedding=emb.embed("loves hiking in the mountains"))
    cooking = EpisodicMemory(user_id="u1", summary="bakes sourdough bread at home",
                             embedding=emb.embed("bakes sourdough bread at home"))
    scored = [ScoredMemory(memory=hiking), ScoredMemory(memory=cooking)]
    resp = emb.embed("we talked about hiking in the mountains today")
    used = used_memory_ids(resp, scored, threshold=0.1)
    assert hiking.memory_id in used
    assert cooking.memory_id not in used


def test_gate_empty_response_embedding_returns_empty():
    assert used_memory_ids([], [], threshold=0.5) == set()
