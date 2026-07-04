"""Groq client — wraps the official `groq` SDK (OpenAI-compatible, synchronous)."""
from __future__ import annotations

from typing import Iterator

from groq import Groq

from infra.llm.base_client import LLMClient


class GroqClient(LLMClient):
    def __init__(self, model: str, api_key: str, base_url: str | None = None, *,
                 temperature: float | None = None, max_tokens: int | None = None):
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = Groq(api_key=api_key, base_url=base_url) if base_url else Groq(api_key=api_key)

    def _params(self, temperature, max_tokens) -> dict:
        p = {}
        t = self._temperature if temperature is None else temperature
        m = self._max_tokens if max_tokens is None else max_tokens
        if t is not None:
            p["temperature"] = t
        if m is not None:
            p["max_tokens"] = m
        return p

    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None) -> str:
        resp = self._client.chat.completions.create(
            model=self._model, messages=self._messages(prompt, system),
            **self._params(temperature, max_tokens))
        return resp.choices[0].message.content

    def stream(self, prompt, *, system=None, temperature=None, max_tokens=None) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self._model, messages=self._messages(prompt, system), stream=True,
            **self._params(temperature, max_tokens))
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Groq does not provide an embeddings endpoint")
