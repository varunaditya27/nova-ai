"""Tests for Layer 2 embedding utilities (cosine, deterministic embedder, vector index).

The production embedder is all-MiniLM-L6-v2 (384-dim) and the index is hnswlib; both sit
behind protocols so a pure-Python, offline deterministic embedder + brute-force index drive
the tests and dev environment without any model or native dependency.
"""

import math

from backend.layer2_memory import embedding as emb


def test_cosine_identical_vectors_is_one():
    v = [0.1, 0.2, 0.3, 0.4]
    assert math.isclose(emb.cosine_similarity(v, v), 1.0, abs_tol=1e-9)


def test_cosine_orthogonal_is_zero():
    assert emb.cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_opposite_is_negative_one():
    assert emb.cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == -1.0


def test_cosine_zero_vector_is_zero():
    assert emb.cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_deterministic_embedder_is_stable():
    e = emb.DeterministicEmbedder(dim=64)
    assert e.embed("placement anxiety") == e.embed("placement anxiety")


def test_deterministic_embedder_dimension_and_norm():
    e = emb.DeterministicEmbedder(dim=128)
    v = e.embed("hello world")
    assert len(v) == 128
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, abs_tol=1e-9)


def test_deterministic_embedder_distinguishes_text():
    e = emb.DeterministicEmbedder(dim=64)
    assert emb.cosine_similarity(e.embed("cats"), e.embed("cats")) == 1.0
    assert emb.cosine_similarity(e.embed("cats"), e.embed("quantum physics")) < 0.9


def test_brute_force_index_search_orders_by_similarity():
    e = emb.DeterministicEmbedder(dim=64)
    index = emb.BruteForceVectorIndex()
    index.add("a", e.embed("placement interview tomorrow"))
    index.add("b", e.embed("placement interview tomorrow"))   # same as query
    index.add("c", e.embed("favorite pizza topping"))
    results = index.search(e.embed("placement interview tomorrow"), top_k=3)
    assert results[0][0] == "b" or results[0][0] == "a"     # the matching ones rank first
    assert results[-1][0] == "c"                             # unrelated ranks last


def test_brute_force_index_respects_top_k():
    e = emb.DeterministicEmbedder(dim=32)
    index = emb.BruteForceVectorIndex()
    for i in range(5):
        index.add(str(i), e.embed(f"text {i}"))
    assert len(index.search(e.embed("text 0"), top_k=2)) == 2


def test_empty_index_returns_empty():
    index = emb.BruteForceVectorIndex()
    assert index.search([0.1, 0.2], top_k=3) == []
