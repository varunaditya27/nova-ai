import pytest
pytest.importorskip("ollama")

from infra.llm import build_llm_client, build_llm_clients, OllamaClient

CFG = {
    "llm": {
        "system1": {"provider": "ollama", "model": "qwen2.5:7b", "temperature": 0.5},
        "system2": {"provider": "ollama", "model": "qwen2.5:7b", "temperature": 0.7},
        "embeddings": {"provider": "ollama", "model": "nomic-embed-text"},
        "providers": {
            "ollama": {"base_url": "http://ollama:11434"},
        },
    }
}


def test_system2_builds_ollama_client_with_model():
    client = build_llm_client("system2", CFG)
    assert isinstance(client, OllamaClient)
    assert client._model == "qwen2.5:7b"


def test_system1_builds_ollama_client():
    client = build_llm_client("system1", CFG)
    assert isinstance(client, OllamaClient)
    assert client._model == "qwen2.5:7b"


def test_build_all_returns_three_clients():
    clients = build_llm_clients(CFG)
    assert set(clients) == {"system1", "system2", "embed"}
    assert isinstance(clients["embed"], OllamaClient)


def test_unknown_provider_raises():
    bad = {"llm": {"x": {"provider": "acme", "model": "m"}, "providers": {}}}
    with pytest.raises(ValueError):
        build_llm_client("x", bad)
