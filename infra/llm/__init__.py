"""LLM infrastructure — provider-agnostic clients + a config-driven factory.

`build_llm_client(role, config)` reads `config['llm'][role]['provider']` and returns the matching
concrete client wired with that role's model/params and the provider's connection settings. Swapping a
role to a different provider is a one-line YAML change (see config/defaults.yaml).
"""
from __future__ import annotations

from infra.llm.base_client import LLMClient
from infra.llm.groq_client import GroqClient
from infra.llm.ollama_client import OllamaClient

__all__ = ["LLMClient", "GroqClient", "OllamaClient", "build_llm_client", "build_llm_clients"]


def build_llm_client(role: str, config: dict) -> LLMClient:
    role_cfg = config["llm"][role]
    provider = role_cfg["provider"]
    conn = config["llm"].get("providers", {}).get(provider, {})
    model = role_cfg["model"]
    temperature = role_cfg.get("temperature")
    max_tokens = role_cfg.get("max_tokens")

    if provider == "groq":
        return GroqClient(model=model, api_key=conn.get("api_key", ""),
                          base_url=conn.get("base_url"),
                          temperature=temperature, max_tokens=max_tokens)
    if provider == "ollama":
        return OllamaClient(model=model, base_url=conn["base_url"],
                            temperature=temperature, max_tokens=max_tokens)
    raise ValueError(f"unknown LLM provider {provider!r} for role {role!r}")


def build_llm_clients(config: dict) -> dict:
    return {
        "system1": build_llm_client("system1", config),
        "system2": build_llm_client("system2", config),
        "embed": build_llm_client("embeddings", config),
    }
