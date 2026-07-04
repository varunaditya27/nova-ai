from infra.vector_store.embedding_fn import OllamaEmbeddingFunction


class _FakeEmbed:
    def embed(self, texts):
        return [[float(len(t))] for t in texts]


def test_embedding_fn_delegates_to_client():
    fn = OllamaEmbeddingFunction(_FakeEmbed())
    assert fn(["ab", "cde"]) == [[2.0], [3.0]]
