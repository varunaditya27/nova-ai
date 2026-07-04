"""Ollama client — wraps the official `ollama` SDK (synchronous)."""
from __future__ import annotations

from typing import Iterator

import ollama

from infra.llm.base_client import LLMClient


class OllamaClient(LLMClient):
    def __init__(self, model: str, base_url: str, *,
                 temperature: float | None = None, max_tokens: int | None = None):
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = ollama.Client(host=base_url)

    def _options(self, temperature, max_tokens) -> dict:
        opts = {}
        t = self._temperature if temperature is None else temperature
        m = self._max_tokens if max_tokens is None else max_tokens
        if t is not None:
            opts["temperature"] = t
        if m is not None:
            opts["num_predict"] = m
        return opts

    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None) -> str:
        resp = self._client.chat(
            model=self._model, messages=self._messages(prompt, system),
            options=self._options(temperature, max_tokens))
        return resp["message"]["content"]

    def stream(self, prompt, *, system=None, temperature=None, max_tokens=None) -> Iterator[str]:
        for part in self._client.chat(
                model=self._model, messages=self._messages(prompt, system), stream=True,
                options=self._options(temperature, max_tokens)):
            piece = part["message"]["content"]
            if piece:
                yield piece

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._client.embeddings(model=self._model, prompt=t)["embedding"] for t in texts]
