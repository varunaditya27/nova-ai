import pytest
pytest.importorskip("groq")

from types import SimpleNamespace

from infra.llm.groq_client import GroqClient
from infra.llm.base_client import LLMClient


def _fake_completion(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_groq_client_is_llmclient():
    assert issubclass(GroqClient, LLMClient)


def test_complete_sends_system_and_user_and_returns_text(mocker):
    sdk = mocker.patch("infra.llm.groq_client.Groq")
    inst = sdk.return_value
    inst.chat.completions.create.return_value = _fake_completion("hi there")

    client = GroqClient(model="llama-3.3-70b-versatile", api_key="sk-x", temperature=0.7)
    out = client.complete("hello", system="be nice")

    assert out == "hi there"
    kwargs = inst.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert kwargs["messages"] == [
        {"role": "system", "content": "be nice"},
        {"role": "user", "content": "hello"},
    ]
    assert kwargs["temperature"] == 0.7


def test_embed_not_supported():
    client = GroqClient(model="m", api_key="k")
    with pytest.raises(NotImplementedError):
        client.embed(["x"])
