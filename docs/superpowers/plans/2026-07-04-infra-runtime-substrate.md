# Infra Runtime Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the production runtime substrate (`config/` loader, `infra/` LLM + vector + DB
clients, `pyproject.toml`, and a fully-dockerised topology) so the already-complete 13-layer
architecture can run against real backends.

**Architecture:** Every layer is dependency-injected and calls injected *synchronous* callables. This
increment supplies the concrete objects that satisfy those injection seams — nothing in `backend/`
changes. LLM access hides behind one `LLMClient` ABC (official `groq`/`ollama` SDKs); vectors live in
ChromaDB (a service); structured state lives in PostgreSQL via SQLAlchemy 2.x. A role-based YAML config
lets each LLM role pick its provider with a one-line change.

**Tech Stack:** Python 3.11 (stdlib base), PyYAML, `groq`, `ollama`, `chromadb`, `sqlalchemy>=2`,
`psycopg[binary]`, pytest, Docker Compose.

## Global Constraints

- Python interpreter for tests: `/usr/bin/python3.11` (3.11.15).
- The base package install MUST remain pure-stdlib; all third-party runtime deps live under the
  `pyproject.toml` optional extra `infra`. The existing 1120 offline tests must stay green and
  offline, untouched.
- Every new infra unit test that imports a third-party SDK MUST guard with
  `pytest.importorskip("<pkg>")` at module top, so `pytest tests/` passes whether or not the `infra`
  extra is installed.
- All infra clients are **synchronous** (the orchestrator calls injected callables synchronously).
- Docker integration tests MUST carry `@pytest.mark.docker` and auto-skip when the target service is
  unreachable — they never run under the default `pytest tests/` collection breaking.
- Vector store is **ChromaDB** (supersedes hnswlib). Postgres is relational-only (no pgvector).
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Config secrets/hosts come from env via `${VAR}` / `${VAR:-default}` interpolation — never hardcode
  an API key.

---

### Task 1: Dependency manifest + config loader + real defaults

**Files:**
- Create: `pyproject.toml`
- Modify: `config/__init__.py` (currently comment-only)
- Create: `config/defaults.yaml` (currently comment-only — overwrite)
- Test: `tests/unit/infra/test_config_loader.py`
- Create: `tests/unit/infra/__init__.py` (empty)

**Interfaces:**
- Produces: `config.load_config(*names: str, env: Mapping[str,str] = os.environ) -> dict` — loads
  `config/defaults.yaml`, deep-merges each named override YAML (in order), then resolves `${VAR}` and
  `${VAR:-default}` placeholders from `env`. Missing override files are ignored; a missing
  `defaults.yaml` raises `FileNotFoundError`.
- Produces: config dict shape with top-level keys `system`, `llm`, `memory`, `timing`; `llm` has
  `system1`/`system2`/`embeddings` role dicts (each with `provider`, `model`) and a `providers` map
  (`groq`, `ollama`).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/test_config_loader.py
import textwrap
import pytest
from config import load_config


def test_load_defaults_returns_role_based_llm_config():
    cfg = load_config(env={"GROQ_API_KEY": "sk-test"})
    assert cfg["llm"]["system1"]["provider"] == "ollama"
    assert cfg["llm"]["system2"]["provider"] == "groq"
    assert cfg["llm"]["embeddings"]["model"] == "nomic-embed-text"


def test_env_interpolation_resolves_secret():
    cfg = load_config(env={"GROQ_API_KEY": "sk-live-123"})
    assert cfg["llm"]["providers"]["groq"]["api_key"] == "sk-live-123"


def test_env_default_used_when_var_absent():
    cfg = load_config(env={"GROQ_API_KEY": "x"})  # OLLAMA_BASE_URL absent
    assert cfg["llm"]["providers"]["ollama"]["base_url"] == "http://ollama:11434"


def test_override_file_deep_merges(tmp_path, monkeypatch):
    override = tmp_path / "prod.yaml"
    override.write_text(textwrap.dedent("""
        llm:
          system2:
            provider: ollama
    """))
    cfg = load_config(str(override), env={"GROQ_API_KEY": "x"})
    assert cfg["llm"]["system2"]["provider"] == "ollama"
    # untouched sibling keys survive the deep merge
    assert cfg["llm"]["system2"]["model"] == "llama-3.3-70b-versatile"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_config_loader.py -v`
Expected: FAIL (ImportError: cannot import name 'load_config' / defaults.yaml has no keys).

- [ ] **Step 3: Write `config/defaults.yaml`**

```yaml
# Nova AI — default configuration (loaded first; override files deep-merge over this).
system:
  database_url: ${DATABASE_URL:-postgresql+psycopg://nova:nova@postgres:5432/nova}
  chroma_host: ${CHROMA_HOST:-chroma}
  chroma_port: ${CHROMA_PORT:-8000}
  debug_mode: false

llm:
  system1:
    provider: ollama
    model: qwen2.5:7b
    temperature: 0.5
    max_tokens: 1024
  system2:
    provider: groq
    model: llama-3.3-70b-versatile
    temperature: 0.7
    max_tokens: 2048
  embeddings:
    provider: ollama
    model: nomic-embed-text
  providers:
    groq:
      base_url: https://api.groq.com/openai/v1
      api_key: ${GROQ_API_KEY}
    ollama:
      base_url: ${OLLAMA_BASE_URL:-http://ollama:11434}

memory:
  recall_weights: { alpha: 0.40, beta: 0.30, gamma: 0.20, delta: 0.10 }
  softmax_temperature: 0.7
  decay_rate: 0.92

timing:
  system1_timeout_ms: 2000
  system2_timeout_ms: 30000
```

- [ ] **Step 4: Write `config/__init__.py`**

```python
"""Configuration loader.

`load_config()` reads `defaults.yaml` then deep-merges each named override file over it and resolves
`${VAR}` / `${VAR:-default}` placeholders from the environment. Nested dicts merge key-wise; scalars
and lists replace. Secrets and hostnames come from env — never hardcode them in YAML.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent
_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _interpolate(value: Any, env: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: _interpolate(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v, env) for v in value]
    if isinstance(value, str):
        def repl(match: re.Match) -> str:
            token = match.group(1)
            name, _, default = token.partition(":-")
            return env.get(name, default)
        return _PLACEHOLDER.sub(repl, value)
    return value


def _resolve(name: str) -> Path:
    p = Path(name)
    return p if p.is_absolute() else _CONFIG_DIR / p


def load_config(*names: str, env: Mapping[str, str] | None = None) -> dict:
    env = os.environ if env is None else env
    defaults_path = _CONFIG_DIR / "defaults.yaml"
    if not defaults_path.exists():
        raise FileNotFoundError(defaults_path)
    merged: dict = yaml.safe_load(defaults_path.read_text()) or {}
    for name in names:
        path = _resolve(name)
        if not path.exists():
            continue
        merged = _deep_merge(merged, yaml.safe_load(path.read_text()) or {})
    return _interpolate(merged, env)
```

- [ ] **Step 5: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "nova-ai"
version = "0.1.0"
description = "13-layer cognitive architecture for long-term human-AI companionship"
requires-python = ">=3.11"
dependencies = []            # base install is pure-stdlib; the 1120 offline tests need nothing here

[project.optional-dependencies]
infra = [
    "pyyaml>=5.4",
    "groq>=0.11",
    "ollama>=0.3",
    "chromadb>=0.5",
    "sqlalchemy>=2",
    "psycopg[binary]>=3.1",
]
dev = [
    "nova-ai[infra]",
    "pytest>=7",
    "pytest-mock>=3",
]

[tool.setuptools]
packages = ["config", "infra", "backend"]

[tool.pytest.ini_options]
markers = [
    "docker: integration test requiring a live dockerised service (auto-skips when unreachable)",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_config_loader.py -v`
Expected: 4 passed.

- [ ] **Step 7: Confirm the full offline suite is still green**

Run: `/usr/bin/python3.11 -m pytest tests/ -q`
Expected: `1124 passed` (1120 existing + 4 new).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml config/__init__.py config/defaults.yaml tests/unit/infra/
git commit -m "feat(infra): config loader, real defaults, and pyproject deps manifest

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: LLM client ABC + Groq client

**Files:**
- Create: `infra/llm/__init__.py` (temporary export stub; fleshed out in Task 4)
- Create: `infra/llm/base_client.py`
- Create: `infra/llm/groq_client.py`
- Test: `tests/unit/infra/test_groq_client.py`

**Interfaces:**
- Produces: `infra.llm.base_client.LLMClient` — abstract sync base with
  `complete(prompt, *, system=None, temperature=None, max_tokens=None) -> str`,
  `stream(prompt, *, system=None, temperature=None, max_tokens=None) -> Iterator[str]`,
  `embed(texts: list[str]) -> list[list[float]]`.
- Produces: `infra.llm.groq_client.GroqClient(model, api_key, base_url=None, *, temperature=None,
  max_tokens=None)`. `embed` raises `NotImplementedError`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/test_groq_client.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_groq_client.py -v`
Expected: FAIL (module not found) — or SKIP if `groq` not installed. If skipped, install first:
`/usr/bin/python3.11 -m pip install -e ".[infra]"` (if the environment blocks pip, the guard keeps
CI green and you verify via the Docker suite in Task 9).

- [ ] **Step 3: Write `infra/llm/base_client.py`**

```python
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
```

- [ ] **Step 4: Write `infra/llm/groq_client.py`**

```python
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
```

- [ ] **Step 5: Write temporary `infra/llm/__init__.py`**

```python
from infra.llm.base_client import LLMClient
from infra.llm.groq_client import GroqClient

__all__ = ["LLMClient", "GroqClient"]
```

Also create `infra/__init__.py` if absent with a one-line docstring: `"""Runtime infrastructure."""`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_groq_client.py -v`
Expected: 3 passed (or skipped if `groq` uninstalled — acceptable per Global Constraints).

- [ ] **Step 7: Commit**

```bash
git add infra/ tests/unit/infra/test_groq_client.py
git commit -m "feat(infra): LLMClient ABC and Groq SDK client

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Ollama client

**Files:**
- Create: `infra/llm/ollama_client.py`
- Test: `tests/unit/infra/test_ollama_client.py`

**Interfaces:**
- Produces: `infra.llm.ollama_client.OllamaClient(model, base_url, *, temperature=None,
  max_tokens=None)` implementing `LLMClient`. `embed(texts)` returns one vector per input text via the
  SDK's `embeddings(model, prompt)` call.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/test_ollama_client.py
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


def test_embed_returns_one_vector_per_text(mocker):
    sdk = mocker.patch("infra.llm.ollama_client.ollama")
    sdk.Client.return_value.embeddings.side_effect = [
        {"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]},
    ]
    client = OllamaClient(model="nomic-embed-text", base_url="http://ollama:11434")
    vecs = client.embed(["a", "b"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_ollama_client.py -v`
Expected: FAIL (module not found) or SKIP if `ollama` uninstalled.

- [ ] **Step 3: Write `infra/llm/ollama_client.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_ollama_client.py -v`
Expected: 3 passed (or skipped if `ollama` uninstalled).

- [ ] **Step 5: Commit**

```bash
git add infra/llm/ollama_client.py tests/unit/infra/test_ollama_client.py
git commit -m "feat(infra): Ollama SDK client (chat, stream, embeddings)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: LLM factory

**Files:**
- Modify: `infra/llm/__init__.py`
- Test: `tests/unit/infra/test_llm_factory.py`

**Interfaces:**
- Consumes: `GroqClient`, `OllamaClient`, `config.load_config`.
- Produces: `infra.llm.build_llm_client(role: str, config: dict) -> LLMClient` — reads
  `config['llm'][role]['provider']`, merges the provider connection config with the role's
  model/params, returns the concrete client.
- Produces: `infra.llm.build_llm_clients(config: dict) -> dict` → keys `system1`, `system2`, `embed`
  (the `embed` client is built from the `embeddings` role).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/test_llm_factory.py
import pytest
pytest.importorskip("groq")
pytest.importorskip("ollama")

from infra.llm import build_llm_client, build_llm_clients, GroqClient, OllamaClient

CFG = {
    "llm": {
        "system1": {"provider": "ollama", "model": "qwen2.5:7b", "temperature": 0.5},
        "system2": {"provider": "groq", "model": "llama-3.3-70b-versatile", "temperature": 0.7},
        "embeddings": {"provider": "ollama", "model": "nomic-embed-text"},
        "providers": {
            "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key": "sk-x"},
            "ollama": {"base_url": "http://ollama:11434"},
        },
    }
}


def test_system2_builds_groq_client_with_model():
    client = build_llm_client("system2", CFG)
    assert isinstance(client, GroqClient)
    assert client._model == "llama-3.3-70b-versatile"


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_llm_factory.py -v`
Expected: FAIL (`build_llm_client` not exported).

- [ ] **Step 3: Write `infra/llm/__init__.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_llm_factory.py -v`
Expected: 4 passed (or skipped if SDKs uninstalled).

- [ ] **Step 5: Commit**

```bash
git add infra/llm/__init__.py tests/unit/infra/test_llm_factory.py
git commit -m "feat(infra): config-driven LLM client factory (role -> provider)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Chroma vector store + collections + embedding function

**Files:**
- Create: `infra/vector_store/__init__.py`
- Create: `infra/vector_store/collections.py`
- Create: `infra/vector_store/chroma_client.py`
- Create: `infra/vector_store/embedding_fn.py`
- Test: `tests/unit/infra/test_embedding_fn.py`

**Interfaces:**
- Produces: `infra.vector_store.collections.COLLECTIONS` — dict mapping logical name →
  `{"name": str, "metadata": {"hnsw:space": "cosine"}}` for `episodic`, `semantic`, `identity`.
- Produces: `infra.vector_store.chroma_client.ChromaVectorStore(host, port)` with
  `add(collection, ids, embeddings, metadatas=None, documents=None)`,
  `query(collection, embedding, n_results=3, where=None) -> list[dict]`,
  `delete(collection, ids)`.
- Produces: `infra.vector_store.embedding_fn.OllamaEmbeddingFunction(client)` — callable
  `__call__(input: list[str]) -> list[list[float]]` delegating to `client.embed`.
- Produces: `infra.vector_store.build_vector_store(config) -> ChromaVectorStore`.

- [ ] **Step 1: Write the failing test** (embedding fn is offline-testable without a live Chroma)

```python
# tests/unit/infra/test_embedding_fn.py
from infra.vector_store.embedding_fn import OllamaEmbeddingFunction


class _FakeEmbed:
    def embed(self, texts):
        return [[float(len(t))] for t in texts]


def test_embedding_fn_delegates_to_client():
    fn = OllamaEmbeddingFunction(_FakeEmbed())
    assert fn(["ab", "cde"]) == [[2.0], [3.0]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_embedding_fn.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write `infra/vector_store/collections.py`**

```python
"""Canonical Chroma collections for Layer 2 memory embeddings (cosine space)."""

_COSINE = {"hnsw:space": "cosine"}

COLLECTIONS = {
    "episodic": {"name": "episodic_memory", "metadata": _COSINE},
    "semantic": {"name": "semantic_memory", "metadata": _COSINE},
    "identity": {"name": "identity_memory", "metadata": _COSINE},
}
```

- [ ] **Step 4: Write `infra/vector_store/embedding_fn.py`**

```python
"""Chroma-compatible embedding function backed by an LLMClient (Ollama nomic-embed-text)."""
from __future__ import annotations


class OllamaEmbeddingFunction:
    """Implements Chroma's EmbeddingFunction protocol: __call__(input) -> embeddings."""

    def __init__(self, client):
        self._client = client

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002 (Chroma's arg name)
        return self._client.embed(list(input))

    def name(self) -> str:
        return "ollama-embedding-function"
```

- [ ] **Step 5: Write `infra/vector_store/chroma_client.py`**

```python
"""ChromaDB vector store wrapper (HttpClient against the dockerised chroma service)."""
from __future__ import annotations

import chromadb

from infra.vector_store.collections import COLLECTIONS


class ChromaVectorStore:
    def __init__(self, host: str, port: int):
        self._client = chromadb.HttpClient(host=host, port=int(port))

    def _collection(self, logical: str):
        spec = COLLECTIONS[logical]
        return self._client.get_or_create_collection(name=spec["name"], metadata=spec["metadata"])

    def add(self, collection, ids, embeddings, metadatas=None, documents=None):
        self._collection(collection).add(
            ids=list(ids), embeddings=list(embeddings),
            metadatas=metadatas, documents=documents)

    def query(self, collection, embedding, n_results=3, where=None) -> list[dict]:
        res = self._collection(collection).query(
            query_embeddings=[list(embedding)], n_results=n_results, where=where)
        ids = res.get("ids", [[]])[0]
        dists = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        docs = res.get("documents", [[]])[0]
        return [
            {"id": ids[i], "distance": dists[i] if dists else None,
             "metadata": metas[i] if metas else None,
             "document": docs[i] if docs else None}
            for i in range(len(ids))
        ]

    def delete(self, collection, ids):
        self._collection(collection).delete(ids=list(ids))
```

- [ ] **Step 6: Write `infra/vector_store/__init__.py`**

```python
"""Vector store infrastructure — ChromaDB service client + Ollama embedding function."""
from __future__ import annotations

from infra.vector_store.chroma_client import ChromaVectorStore
from infra.vector_store.collections import COLLECTIONS
from infra.vector_store.embedding_fn import OllamaEmbeddingFunction

__all__ = ["ChromaVectorStore", "COLLECTIONS", "OllamaEmbeddingFunction", "build_vector_store"]


def build_vector_store(config: dict) -> ChromaVectorStore:
    sysc = config["system"]
    return ChromaVectorStore(host=sysc["chroma_host"], port=sysc["chroma_port"])
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_embedding_fn.py -v`
Expected: 1 passed.

- [ ] **Step 8: Commit**

```bash
git add infra/vector_store/ tests/unit/infra/test_embedding_fn.py
git commit -m "feat(infra): ChromaDB vector store, collections, and Ollama embedding fn

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Postgres engine + session scope

**Files:**
- Create: `infra/db/__init__.py`
- Create: `infra/db/base.py`
- Create: `infra/db/engine.py`
- Test: `tests/unit/infra/test_db_engine.py`

**Interfaces:**
- Produces: `infra.db.base.Base` — SQLAlchemy 2.x `DeclarativeBase` subclass with a constraint naming
  convention.
- Produces: `infra.db.engine.make_engine(url: str)`, `make_session_factory(engine)`,
  `session_scope(session_factory)` context manager (commit on success, rollback on error, always
  close), `init_db(engine)` calling `Base.metadata.create_all(engine)`.

- [ ] **Step 1: Write the failing test** (offline: in-memory SQLite proves the plumbing)

```python
# tests/unit/infra/test_db_engine.py
import pytest
pytest.importorskip("sqlalchemy")

from sqlalchemy import text
from infra.db.engine import make_engine, make_session_factory, session_scope


def test_session_scope_commits_and_closes():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        result = session.execute(text("select 1")).scalar_one()
    assert result == 1


def test_session_scope_rolls_back_on_error():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    factory = make_session_factory(engine)
    with pytest.raises(ValueError):
        with session_scope(factory) as session:
            session.execute(text("select 1"))
            raise ValueError("boom")
    # no assertion beyond: the context manager must not swallow the error
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_db_engine.py -v`
Expected: FAIL (module not found) or SKIP if sqlalchemy uninstalled.

- [ ] **Step 3: Write `infra/db/base.py`**

```python
"""SQLAlchemy declarative base with a constraint naming convention (stable migration names)."""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_CONVENTION)
```

- [ ] **Step 4: Write `infra/db/engine.py`**

```python
"""Postgres engine, session factory, and transactional scope."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infra.db.base import Base


def make_engine(url: str):
    return create_engine(url, future=True, pool_pre_ping=True)


def make_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine) -> None:
    """Create all tables (dev/bootstrap path; Alembic migrations are a later increment)."""
    import infra.db.models  # noqa: F401 — ensure all models are registered on Base.metadata
    Base.metadata.create_all(engine)
```

- [ ] **Step 5: Write `infra/db/__init__.py`**

```python
"""Relational (Postgres) infrastructure — declarative base, engine, session scope."""
from __future__ import annotations

from infra.db.base import Base
from infra.db.engine import init_db, make_engine, make_session_factory, session_scope

__all__ = ["Base", "make_engine", "make_session_factory", "session_scope", "init_db"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_db_engine.py -v`
Expected: 2 passed (or skipped if sqlalchemy uninstalled).

- [ ] **Step 7: Commit**

```bash
git add infra/db/__init__.py infra/db/base.py infra/db/engine.py tests/unit/infra/test_db_engine.py
git commit -m "feat(infra): SQLAlchemy base, engine, and transactional session scope

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Postgres ORM models (all 14)

**Files:**
- Create: `infra/db/models/__init__.py`
- Create: `infra/db/models/session.py`, `memory.py`, `persona.py`, `relationship.py`, `goals.py`,
  `proactivity.py`, `safety.py`, `privacy.py`, `longitudinal.py`, `tools.py`, `output_prefs.py`,
  `onboarding.py`
- Test: `tests/unit/infra/test_db_models.py`

**Interfaces:**
- Consumes: `infra.db.base.Base`, `infra.db.engine.{make_engine,make_session_factory,session_scope,init_db}`.
- Produces: 14 ORM classes registered on `Base.metadata`. Every table has an integer PK `id` and a
  `created_at` timestamp; user-scoped tables carry a `user_id: str` column. `infra.db.models.__init__`
  re-exports all classes and defines `__all__`.

Note: models are mechanical and interdependent only through `Base`, so they are implemented and tested
together — a reviewer would accept/reject the ORM schema as one unit. Keep each file to its named
concern; do not add relationships beyond `user_id` scoping in this increment.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/test_db_models.py
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from infra.db.base import Base
from infra.db.engine import make_engine, make_session_factory, session_scope, init_db
import infra.db.models as models


EXPECTED_TABLES = {
    "session", "episodic_memory", "semantic_memory", "identity_memory", "memory_audit",
    "persona_state", "relationship_state", "goal", "proactive_item", "safety_event",
    "privacy_audit", "longitudinal_summary", "tool_action", "output_pref", "onboarding_state",
}


def test_all_tables_registered():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_create_all_and_insert_roundtrip():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.EpisodicMemory(user_id="u1", summary="first chat", importance=0.5))
    with session_scope(factory) as s:
        row = s.query(models.EpisodicMemory).filter_by(user_id="u1").one()
        assert row.summary == "first chat"
        assert isinstance(row.created_at, datetime)


def test_goal_model_has_status_and_user_scope():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.Goal(user_id="u1", description="run 5k", status="active"))
    with session_scope(factory) as s:
        assert s.query(models.Goal).filter_by(status="active").count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_db_models.py -v`
Expected: FAIL (models package empty).

- [ ] **Step 3: Write a shared mixin and the model files**

Create `infra/db/models/_mixins.py`:

```python
"""Shared column mixins for ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class UserScopedMixin(TimestampMixin):
    user_id: Mapped[str] = mapped_column(String(64), index=True)
```

Create `infra/db/models/session.py`:

```python
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin


class Session(UserScopedMixin, Base):
    __tablename__ = "session"
    session_key: Mapped[str] = mapped_column(String(64), unique=True)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
```

Create `infra/db/models/memory.py`:

```python
from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import TimestampMixin, UserScopedMixin


class EpisodicMemory(UserScopedMixin, Base):
    __tablename__ = "episodic_memory"
    summary: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float, default=0.0)
    vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)


class SemanticMemory(UserScopedMixin, Base):
    __tablename__ = "semantic_memory"
    fact: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    support_count: Mapped[int] = mapped_column(Integer, default=1)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False)


class IdentityMemory(TimestampMixin, Base):
    __tablename__ = "identity_memory"
    key: Mapped[str] = mapped_column(String(128), index=True)
    value: Mapped[str] = mapped_column(Text)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False)


class MemoryAudit(UserScopedMixin, Base):
    __tablename__ = "memory_audit"
    event: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64))
```

Create the remaining model files, each following the same pattern (all inherit `UserScopedMixin, Base`
unless noted). Use these exact tablenames and key columns:

`infra/db/models/persona.py` — `class PersonaState`: `__tablename__ = "persona_state"`;
`warmth: Mapped[float]`, `verbosity: Mapped[float]`, `formality: Mapped[float]` (all `Float`, default 0.5).

`infra/db/models/relationship.py` — `class RelationshipState`: `__tablename__ = "relationship_state"`;
`stage: Mapped[str]` (`String(32)`, default "new"), `trust: Mapped[float]` (`Float`, default 0.0).

`infra/db/models/goals.py` — `class Goal`: `__tablename__ = "goal"`;
`description: Mapped[str]` (`Text`), `status: Mapped[str]` (`String(32)`, default "active"),
`progress: Mapped[float]` (`Float`, default 0.0).

`infra/db/models/proactivity.py` — `class ProactiveItem`: `__tablename__ = "proactive_item"`;
`kind: Mapped[str]` (`String(48)`), `payload: Mapped[str]` (`Text`),
`status: Mapped[str]` (`String(32)`, default "queued").

`infra/db/models/safety.py` — `class SafetyEvent`: `__tablename__ = "safety_event"`;
`tier: Mapped[str]` (`String(16)`), `detail: Mapped[str]` (`Text`),
`resolved: Mapped[bool]` (`Boolean`, default False).

`infra/db/models/privacy.py` — `class PrivacyAudit`: `__tablename__ = "privacy_audit"`;
`action: Mapped[str]` (`String(48)`), `detail: Mapped[str]` (`Text`),
`prev_hash: Mapped[str | None]` (`String(64)`, nullable), `entry_hash: Mapped[str]` (`String(64)`).

`infra/db/models/longitudinal.py` — `class LongitudinalSummary`: `__tablename__ = "longitudinal_summary"`;
`period: Mapped[str]` (`String(32)`), `summary: Mapped[str]` (`Text`).

`infra/db/models/tools.py` — `class ToolAction`: `__tablename__ = "tool_action"`;
`tool: Mapped[str]` (`String(48)`), `params: Mapped[str]` (`Text`),
`outcome: Mapped[str]` (`String(32)`, default "recorded").

`infra/db/models/output_prefs.py` — `class OutputPref`: `__tablename__ = "output_pref"`;
`channel: Mapped[str]` (`String(32)`, default "text"), `voice: Mapped[str | None]` (`String(48)`, nullable).

`infra/db/models/onboarding.py` — `class OnboardingState`: `__tablename__ = "onboarding_state"`;
`cold_start_active: Mapped[bool]` (`Boolean`, default True), `session_index: Mapped[int]` (`Integer`, default 0).

Each file imports `from sqlalchemy import Boolean, Float, Integer, String, Text` (as needed),
`from sqlalchemy.orm import Mapped, mapped_column`, `from infra.db.base import Base`, and
`from infra.db.models._mixins import UserScopedMixin` (or `TimestampMixin` for IdentityMemory).

- [ ] **Step 4: Write `infra/db/models/__init__.py`**

```python
"""ORM models mapping per-layer relational state. Importing this registers every table on Base.metadata."""
from __future__ import annotations

from infra.db.models.session import Session
from infra.db.models.memory import EpisodicMemory, SemanticMemory, IdentityMemory, MemoryAudit
from infra.db.models.persona import PersonaState
from infra.db.models.relationship import RelationshipState
from infra.db.models.goals import Goal
from infra.db.models.proactivity import ProactiveItem
from infra.db.models.safety import SafetyEvent
from infra.db.models.privacy import PrivacyAudit
from infra.db.models.longitudinal import LongitudinalSummary
from infra.db.models.tools import ToolAction
from infra.db.models.output_prefs import OutputPref
from infra.db.models.onboarding import OnboardingState

__all__ = [
    "Session", "EpisodicMemory", "SemanticMemory", "IdentityMemory", "MemoryAudit",
    "PersonaState", "RelationshipState", "Goal", "ProactiveItem", "SafetyEvent",
    "PrivacyAudit", "LongitudinalSummary", "ToolAction", "OutputPref", "OnboardingState",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_db_models.py -v`
Expected: 3 passed (or skipped if sqlalchemy uninstalled).

- [ ] **Step 6: Commit**

```bash
git add infra/db/models/ tests/unit/infra/test_db_models.py
git commit -m "feat(infra): 14 SQLAlchemy ORM models for per-layer relational state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Docker topology

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Create: `.env.example`
- Create: `.dockerignore`

**Interfaces:**
- Produces: a compose stack — `postgres`, `chroma`, `ollama`, `kokoro` up by default; `backend`
  behind profile `app`. No Python test in this task; verification is `docker compose config`.

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
name: nova-ai

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-nova}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-nova}
      POSTGRES_DB: ${POSTGRES_DB:-nova}
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-nova}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [nova-network]

  chroma:
    image: chromadb/chroma
    ports: ["8001:8000"]
    volumes: ["chromadata:/data"]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v2/heartbeat')"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [nova-network]

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: ["ollamamodels:/root/.ollama"]
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 15s
      timeout: 5s
      retries: 5
    networks: [nova-network]

  kokoro:
    image: ghcr.io/remsky/kokoro-fastapi:latest
    ports: ["8880:8880"]
    networks: [nova-network]

  backend:
    build: .
    profiles: ["app"]              # started only once api/ exists: `docker compose --profile app up`
    ports: ["8000:8000"]
    env_file: [.env]
    depends_on:
      postgres: { condition: service_healthy }
      chroma: { condition: service_healthy }
      ollama: { condition: service_healthy }
    networks: [nova-network]

volumes:
  pgdata:
  chromadata:
  ollamamodels:

networks:
  nova-network:
    driver: bridge
```

- [ ] **Step 2: Write `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[infra]"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write `.env.example`**

```bash
# Copy to .env and fill in. Never commit .env.
GROQ_API_KEY=
DATABASE_URL=postgresql+psycopg://nova:nova@postgres:5432/nova
CHROMA_HOST=chroma
CHROMA_PORT=8000
OLLAMA_BASE_URL=http://ollama:11434
POSTGRES_USER=nova
POSTGRES_PASSWORD=nova
POSTGRES_DB=nova
```

- [ ] **Step 4: Write `.dockerignore`**

```
.git
__pycache__/
*.pyc
tests/
docs/
.env
nova-data/
```

- [ ] **Step 5: Validate compose file parses**

Run: `docker compose config >/dev/null && echo OK`
Expected: `OK` (requires Docker CLI; if unavailable, visually confirm YAML and defer to the user).

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml Dockerfile .env.example .dockerignore
git commit -m "feat(infra): dockerised topology (postgres, chroma, ollama, kokoro, backend)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Docker integration tests (auto-skip offline)

**Files:**
- Create: `tests/integration_infra/__init__.py` (empty)
- Create: `tests/integration_infra/conftest.py`
- Create: `tests/integration_infra/test_infra_services.py`

**Interfaces:**
- Consumes: `config.load_config`, `infra.llm.build_llm_client`, `infra.vector_store.ChromaVectorStore`,
  `infra.db.{make_engine,make_session_factory,session_scope,init_db}`, `infra.db.models`.
- Produces: `@pytest.mark.docker` tests that probe each service and `pytest.skip` when unreachable.

- [ ] **Step 1: Write `tests/integration_infra/conftest.py`**

```python
"""Fixtures for docker-backed infra tests. Every fixture probes its service and skips if it's down,
so `pytest tests/` stays green with no stack running."""
import os
import socket

import pytest


def _reachable(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def ollama_url():
    url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    host = url.split("//", 1)[-1].split(":")[0]
    port = int(url.rsplit(":", 1)[-1])
    if not _reachable(host, port):
        pytest.skip(f"ollama not reachable at {url}")
    return url


@pytest.fixture
def chroma_hostport():
    host = os.environ.get("CHROMA_HOST", "localhost")
    port = int(os.environ.get("CHROMA_PORT", "8001"))
    if not _reachable(host, port):
        pytest.skip(f"chroma not reachable at {host}:{port}")
    return host, port


@pytest.fixture
def postgres_url():
    url = os.environ.get("DATABASE_URL", "postgresql+psycopg://nova:nova@localhost:5432/nova")
    hostport = url.rsplit("@", 1)[-1].split("/", 1)[0]
    host, _, port = hostport.partition(":")
    if not _reachable(host, int(port or 5432)):
        pytest.skip(f"postgres not reachable at {hostport}")
    return url
```

- [ ] **Step 2: Write `tests/integration_infra/test_infra_services.py`**

```python
import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sqlalchemy")

from infra.vector_store import ChromaVectorStore
from infra.db import make_engine, make_session_factory, session_scope, init_db
import infra.db.models as models


@pytest.mark.docker
def test_ollama_complete_and_embed(ollama_url):
    pytest.importorskip("ollama")
    from infra.llm.ollama_client import OllamaClient
    client = OllamaClient(model="qwen2.5:7b", base_url=ollama_url)
    text = client.complete("Say the word ready.")
    assert isinstance(text, str) and text
    vecs = OllamaClient(model="nomic-embed-text", base_url=ollama_url).embed(["hello"])
    assert len(vecs) == 1 and len(vecs[0]) > 0


@pytest.mark.docker
def test_chroma_add_query_delete(chroma_hostport):
    host, port = chroma_hostport
    store = ChromaVectorStore(host=host, port=port)
    store.add("episodic", ids=["m1"], embeddings=[[0.1, 0.2, 0.3]],
              metadatas=[{"user_id": "u1"}], documents=["first"])
    hits = store.query("episodic", [0.1, 0.2, 0.3], n_results=1)
    assert hits and hits[0]["id"] == "m1"
    store.delete("episodic", ["m1"])


@pytest.mark.docker
def test_postgres_model_crud(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.Goal(user_id="itest", description="ship infra", status="active"))
    with session_scope(factory) as s:
        assert s.query(models.Goal).filter_by(user_id="itest").count() >= 1
        s.query(models.Goal).filter_by(user_id="itest").delete()
```

- [ ] **Step 3: Verify offline behaviour (must SKIP, not fail)**

Run: `/usr/bin/python3.11 -m pytest tests/integration_infra/ -v`
Expected: all tests SKIPPED (services unreachable) — never FAILED.

- [ ] **Step 4: Verify the default suite excludes/greens these**

Run: `/usr/bin/python3.11 -m pytest tests/ -q`
Expected: existing + new offline unit tests pass; the docker tests report as skipped, suite still green.

- [ ] **Step 5: Commit**

```bash
git add tests/integration_infra/
git commit -m "test(infra): docker integration tests for ollama, chroma, postgres (auto-skip offline)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Documentation reconciliation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/NOVA_AI_MASTER_ARCHITECTURE.md`
- Modify: `docs/layer-2-architecture.md`

**Interfaces:** none (docs only). This task exists because the ChromaDB decision supersedes hnswlib
across the canonical docs; leaving them contradictory violates the "code and docs are one SSOT" rule.

- [ ] **Step 1: Update `CLAUDE.md` vector-store references**

In the "Infrastructure Stack" and Layer 2 sections, replace hnswlib descriptions with ChromaDB:
- Change "**Vector store**: **hnswlib** (in-process, on-device, no server); all-MiniLM-L6-v2 384-dim"
  to "**Vector store**: **ChromaDB** (runs as its own service/container); embeddings from Ollama
  `nomic-embed-text` via `OllamaEmbeddingFunction`. Cosine space."
- Remove the caveat sentence "Note: `conftest.py` mocks ChromaDB — the architecture spec is hnswlib;
  update tests accordingly when implementing." Replace with: "The production vector store is ChromaDB
  (`infra/vector_store/`); see `docs/superpowers/specs/2026-07-04-infra-runtime-substrate-design.md`."
- In the Episodic Memory bullet, change "embeddings stored in **hnswlib** (`memory.vdb`, ...)" to
  "embeddings stored in **ChromaDB** (`episodic_memory` collection, cosine space)."
- Note Postgres is the relational store; vectors live in Chroma (no pgvector).

- [ ] **Step 2: Update `docs/NOVA_AI_MASTER_ARCHITECTURE.md`**

In the Infrastructure/Storage sections, apply the same hnswlib→ChromaDB change and add a short
"Runtime substrate (`infra/`)" note: config loader + role-based LLM factory (groq/ollama SDKs),
ChromaDB vector store, Postgres/SQLAlchemy models, dockerised via `docker-compose.yml`. Link the design
spec.

- [ ] **Step 3: Update `docs/layer-2-architecture.md`**

Add a one-line as-built correction wherever hnswlib/`memory.vdb` is named: the production embedding
store is ChromaDB (`infra/vector_store/`), superseding the original hnswlib design.

- [ ] **Step 4: Verify no stale hnswlib references remain in canonical docs**

Run: `grep -rin "hnswlib" CLAUDE.md docs/NOVA_AI_MASTER_ARCHITECTURE.md docs/layer-2-architecture.md`
Expected: no matches (or only a clearly-labelled "superseded" historical note).

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md docs/NOVA_AI_MASTER_ARCHITECTURE.md docs/layer-2-architecture.md
git commit -m "docs: ChromaDB supersedes hnswlib as the vector store across canonical docs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Final verification + PR

**Files:** none (verification + integration).

- [ ] **Step 1: Full offline suite green**

Run: `/usr/bin/python3.11 -m pytest tests/ -q`
Expected: all pass; new infra unit tests either pass (if `infra` extra installed) or skip (if not);
docker tests skip. No failures.

- [ ] **Step 2: Config swap smoke check**

Run:
```bash
/usr/bin/python3.11 -c "from config import load_config; c=load_config(env={'GROQ_API_KEY':'x'}); print(c['llm']['system2']['provider'], c['system']['chroma_host'])"
```
Expected: `groq chroma`.

- [ ] **Step 3: Push branch and open PR**

```bash
git push -u origin infra-runtime-substrate
gh pr create --title "feat(infra): runtime substrate — config, LLM/vector/DB clients, docker" \
  --body "$(cat <<'EOF'
Stands up the production runtime substrate under `infra/` so the 13-layer architecture can run against
real backends.

- Config loader with deep-merge + `${ENV}` interpolation; role-based LLM config (one-line provider swap)
- LLMClient ABC + Groq/Ollama official-SDK clients + config-driven factory
- ChromaDB vector store + Ollama embedding function (supersedes hnswlib)
- Postgres SQLAlchemy 2.x engine, session scope, and 14 ORM models
- `pyproject.toml` with an optional `infra` extra (base install stays pure-stdlib)
- Fully dockerised: postgres, chroma, ollama, kokoro (+ backend behind an `app` profile)
- Docker integration tests (auto-skip offline) + offline unit tests for the wiring
- Canonical docs updated: ChromaDB supersedes hnswlib

Design spec: `docs/superpowers/specs/2026-07-04-infra-runtime-substrate-design.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 4: Report the PR URL to the user for review before merge.**

---

## Notes for the implementer

- If `pip install -e ".[infra]"` is blocked in your environment, that's expected — the
  `pytest.importorskip` guards make every infra unit test skip cleanly, and the Docker integration
  suite (Task 9) is the fidelity check the user chose. Do not remove the guards to force the tests to
  run against a missing dependency.
- Do not touch anything under `backend/` — this increment only adds the substrate the layers inject.
- The `backend` compose service intentionally does not start under `docker compose up` (it needs the
  `api/` increment); this is not a bug.
