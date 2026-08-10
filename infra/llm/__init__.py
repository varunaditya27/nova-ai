"""LLM infrastructure — provider-agnostic clients + a config-driven factory.

`build_llm_client(role, config)` reads `config['llm'][role]['provider']` and returns the matching
concrete client wired with that role's model/params and the provider's connection settings. Every
role runs against local Ollama models; which model backs a role is a config/env knob
(see config/defaults.yaml) — the platform runs fully offline.

The concrete client is imported lazily (PEP 562) so pure-stdlib submodules like
``infra.llm.json_extract`` import on a bare interpreter without the provider SDK installed.
"""
from __future__ import annotations

from infra.llm.base_client import LLMClient

__all__ = ["LLMClient", "OllamaClient", "build_llm_client", "build_llm_clients"]


def __getattr__(name: str):
    if name == "OllamaClient":
        from infra.llm.ollama_client import OllamaClient
        return OllamaClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def build_llm_client(role: str, config: dict) -> "LLMClient":
    role_cfg = config["llm"][role]
    provider = role_cfg["provider"]
    conn = config["llm"].get("providers", {}).get(provider, {})
    model = role_cfg["model"]
    temperature = role_cfg.get("temperature")
    max_tokens = role_cfg.get("max_tokens")

    if provider == "ollama":
        from infra.llm.ollama_client import OllamaClient
        return OllamaClient(model=model, base_url=conn["base_url"],
                            temperature=temperature, max_tokens=max_tokens)
    raise ValueError(f"unknown LLM provider {provider!r} for role {role!r}")


def build_llm_clients(config: dict) -> dict:
    clients = {
        "system1": build_llm_client("system1", config),
        "system2": build_llm_client("system2", config),
        "embed": build_llm_client("embeddings", config),
    }
    if "intent" in config.get("llm", {}):        # optional fast small-model for Layer-8 tool intent
        clients["intent"] = build_llm_client("intent", config)
    return clients
