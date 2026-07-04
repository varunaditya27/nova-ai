"""Provider-agnostic synchronous LLM interface.

Layers call injected callables synchronously, so all clients are sync. Concrete providers (Groq,
Ollama) wrap their official SDK and satisfy this ABC; the SDK stays quarantined behind it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator


class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None,
                 temperature: float | None = None, max_tokens: int | None = None) -> str: ...

    @abstractmethod
    def stream(self, prompt: str, *, system: str | None = None,
               temperature: float | None = None, max_tokens: int | None = None) -> Iterator[str]: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @staticmethod
    def _messages(prompt: str, system: str | None) -> list[dict]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs
