import pytest
pytest.importorskip("ollama")

from infra.llm.ollama_client import OllamaClient
from infra.llm.base_client import LLMClient


def test_ollama_client_is_llmclient():
    assert issubclass(OllamaClient, LLMClient)


def test_complete_calls_chat_and_returns_text(mocker):
    sdk = mocker.patch("infra.llm.ollama_client.ollama")
    sdk.Client.return_value.chat.return_value = {"message": {"content": "yo"}}

    client = OllamaClient(model="qwen2.5:7b", base_url="http://ollama:11434", temperature=0.5)
    out = client.complete("hey", system="s")

    assert out == "yo"
    kwargs = sdk.Client.return_value.chat.call_args.kwargs
    assert kwargs["model"] == "qwen2.5:7b"
    assert kwargs["messages"][0] == {"role": "system", "content": "s"}
    assert kwargs["options"]["temperature"] == 0.5
    assert kwargs["think"] is False


def test_embed_returns_one_vector_per_text(mocker):
    sdk = mocker.patch("infra.llm.ollama_client.ollama")
    sdk.Client.return_value.embeddings.side_effect = [
        {"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]},
    ]
    client = OllamaClient(model="nomic-embed-text", base_url="http://ollama:11434")
    vecs = client.embed(["a", "b"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
