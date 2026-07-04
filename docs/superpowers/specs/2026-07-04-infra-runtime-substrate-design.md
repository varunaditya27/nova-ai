# Infra Runtime Substrate — Design Spec

**Date:** 2026-07-04
**Status:** Approved (design), pending implementation plan
**Scope:** Stand up the production runtime substrate under `infra/` (plus config loader,
dependency manifest, and Docker topology) so the already-complete 13-layer cognitive
architecture can run against real backends. This is the "critical path first" increment.

---

## 1. Motivation

All 13 cognitive layers + the pipeline orchestrator are implemented and tested (1120 offline
tests). They are dependency-injected: every LLM call, vector store, embedder, and DB writer is an
injected callable currently filled by test fakes. What does **not** exist yet is the concrete
substrate those injections need in production — `infra/`, `config/`, `api/`, `background/`,
`scripts/` are comment-only scaffolds, and there is no dependency manifest or working
`docker-compose.yml`.

This spec covers **infra/ critical path + the runtime plumbing it depends on**. Out of scope for
this increment (explicit follow-ups): `api/` FastAPI app, `background/` scheduler, `scripts/`,
Alembic migrations, `infra/websocket/`, `infra/session_cache.py`.

## 2. Design decisions (approved)

| Decision | Choice | Rationale |
|---|---|---|
| Vector store | **ChromaDB (as a service)** | User directive. **Supersedes** the hnswlib decision in `CLAUDE.md`/master doc — those get updated. |
| Vectors vs Postgres | Embeddings live **only in Chroma**; Postgres is the plain relational store | No pgvector needed; clean separation. Supersedes the pgvector note in arch docs. |
| Relational DB | **PostgreSQL 16** via SQLAlchemy 2.x (sync) | User directive; sync matches the synchronous orchestrator. |
| LLM clients | **Official SDKs** (`groq`, `ollama`), sync | Best practice: vendor owns retries/streaming/errors. Quarantined behind an ABC. |
| Client style | **Synchronous** | Orchestrator calls injected callables synchronously; no async plumbing. |
| Config | YAML deep-merge loader with `${ENV}` interpolation; **role-based** LLM config | One-line provider swap per role. |
| Deps | `pyproject.toml` with an optional `infra` extra | Base install stays pure-stdlib so the 1120 offline tests are unaffected. |
| Testing | **Docker-based integration tests** (`@pytest.mark.docker`, auto-skip offline) + fast offline unit tests for pure-logic wiring | Real-service fidelity without breaking the offline suite. |
| Deployment | **Fully dockerised**: backend, postgres, chroma, ollama, kokoro | User directive. |

## 3. Components

### 3.1 `config/`
- `config/__init__.py` — real loader:
  - `load_config(*names, env=os.environ) -> dict`. Loads `defaults.yaml`, deep-merges each named
    override file (e.g. `production.yaml`, `layerN.yaml`) in order.
  - Deep-merge: nested dicts merged key-wise; scalars/lists replaced.
  - `${VAR}` / `${VAR:-default}` interpolation resolved from `env` after merge (for secrets/hosts).
  - Missing override file is a no-op; missing `defaults.yaml` is an error.
- `config/defaults.yaml` — real keys (currently comment-only). Includes:
  ```yaml
  system:
    database_url: ${DATABASE_URL:-postgresql+psycopg://nova:nova@postgres:5432/nova}
    chroma_host: ${CHROMA_HOST:-chroma}
    chroma_port: ${CHROMA_PORT:-8000}
    debug_mode: false
  llm:
    system1:    { provider: ollama, model: qwen2.5:7b,              temperature: 0.5, max_tokens: 1024 }
    system2:    { provider: groq,   model: llama-3.3-70b-versatile,  temperature: 0.7, max_tokens: 2048 }
    embeddings: { provider: ollama, model: nomic-embed-text }
    providers:
      groq:   { base_url: https://api.groq.com/openai/v1, api_key: ${GROQ_API_KEY} }
      ollama: { base_url: ${OLLAMA_BASE_URL:-http://ollama:11434} }
  memory:
    recall_weights: { alpha: 0.40, beta: 0.30, gamma: 0.20, delta: 0.10 }
    softmax_temperature: 0.7
    decay_rate: 0.92
  timing:
    system1_timeout_ms: 2000
    system2_timeout_ms: 30000
  ```
  - **Swapping System 2 to local** = change `system2.provider` to `ollama` and set a model. One line.

### 3.2 `infra/llm/`
- `base_client.py` — `LLMClient` ABC (sync):
  - `complete(prompt: str, *, system: str | None = None, temperature: float | None = None, max_tokens: int | None = None) -> str`
  - `stream(prompt, *, system, temperature, max_tokens) -> Iterator[str]`
  - `embed(texts: list[str]) -> list[list[float]]` (raises `NotImplementedError` on providers without embeddings, e.g. Groq)
- `groq_client.py` — `GroqClient(model, api_key, base_url, **defaults)` wrapping `groq.Groq`;
  `complete`/`stream` over `chat.completions.create`. `embed` unsupported.
- `ollama_client.py` — `OllamaClient(model, base_url, **defaults)` wrapping `ollama.Client`;
  `complete`/`stream` over `client.chat`; `embed` over `client.embeddings`.
- `__init__.py`:
  - `build_llm_client(role: str, config: dict) -> LLMClient` — reads `config['llm'][role]['provider']`,
    merges provider connection config + role model/params, returns the concrete client.
  - `build_llm_clients(config) -> dict` → `{"system1": ..., "system2": ..., "embed": ...}`.

### 3.3 `infra/vector_store/`
- `chroma_client.py` — `ChromaVectorStore(host, port)` over `chromadb.HttpClient`:
  - `add(collection, ids, embeddings, metadatas, documents)`
  - `query(collection, embedding, n_results, where=None) -> list[Match]`
  - `delete(collection, ids)`
  - Collections created with cosine space (`hnsw:space=cosine`).
- `embedding_fn.py` — `OllamaEmbeddingFunction` implementing Chroma's `EmbeddingFunction` interface,
  delegating to an `OllamaClient.embed`. Embedding dim follows the model (nomic-embed-text ⇒ 768).
- `collections.py` — canonical collection names/config: `episodic`, `semantic`, `identity`.
- `__init__.py` — `build_vector_store(config) -> ChromaVectorStore`.

### 3.4 `infra/db/`
- `base.py` — SQLAlchemy 2.x `DeclarativeBase` subclass + naming convention for constraints.
- `engine.py` — `make_engine(url)`, `SessionLocal` sessionmaker, `session_scope()` context manager
  (commit/rollback/close), `init_db(engine)` calling `Base.metadata.create_all`.
- `models/*.py` — 14 ORM models mapping layer state:
  `memory` (episodic/semantic/identity rows + audit), `session`, `persona`, `relationship`,
  `goals`, `proactivity`, `safety`, `privacy`, `longitudinal`, `tools`, `output_prefs`,
  `onboarding`. Thin, focused, one concern per file; FKs to a `users`/`session` anchor where natural.
- Alembic migrations **deferred**; `init_db` uses `create_all` for this increment.

### 3.5 `pyproject.toml`
- `[project]` base: pure stdlib (no runtime deps) so `pytest tests/` runs untouched.
- `[project.optional-dependencies]`:
  - `infra = ["groq", "ollama", "chromadb", "sqlalchemy>=2", "psycopg[binary]", "pyyaml"]`
  - `dev = [infra deps + "pytest", "pytest-mock"]`
- `[tool.pytest.ini_options]` — register the `docker` marker; keep default collection on `tests/`.

### 3.6 Docker
- `docker-compose.yml` — services on `nova-network`, each with healthcheck + named volume:
  - `postgres` (`postgres:16`, 5432, volume `pgdata`, env POSTGRES_USER/PASSWORD/DB)
  - `chroma` (`chromadb/chroma`, host 8001 → container 8000, volume `chromadata`)
  - `ollama` (`ollama/ollama`, 11434, volume `ollamamodels`; entrypoint pulls qwen2.5:7b + nomic-embed-text)
  - `kokoro` (TTS, 8880)
  - `backend` (build ., port 8000) — **gated behind a compose profile `app`** and `depends_on`
    postgres/chroma/ollama healthy. `docker compose up -d` brings up the four backing services this
    increment needs; the app container joins via `--profile app` once `api/main.py` exists (next
    increment). This avoids a crash-loop on the not-yet-built FastAPI app while keeping the service
    defined and wired now.
- `Dockerfile` — `python:3.11-slim`; install `.[infra]`; copy source; default CMD `uvicorn
  api.main:app --host 0.0.0.0 --port 8000` (only invoked under the `app` profile, i.e. after the api
  increment). The image builds fine today; it just isn't started by the default `up`.
- `.env.example` — `GROQ_API_KEY`, `DATABASE_URL`, `CHROMA_HOST`, `CHROMA_PORT`, `OLLAMA_BASE_URL`,
  `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

### 3.7 Testing
- **Offline unit tests** (`tests/unit/infra/`, run by default, no containers):
  - config deep-merge + `${ENV}` interpolation + `${VAR:-default}` fallback
  - `build_llm_client` provider selection (patched SDK constructors — assert the right client type +
    wired model/params, no network)
  - `OllamaEmbeddingFunction` shape (patched embed)
- **Docker integration tests** (`tests/integration_infra/`, `@pytest.mark.docker`, **auto-skip when
  the target service is unreachable** via a connectivity probe fixture):
  - Ollama `complete` + `embed` roundtrip
  - Chroma add → query → delete roundtrip (real server)
  - Postgres model CRUD through `session_scope`
- Invariant: `pytest tests/` (default) still reports **1120 + new offline unit tests passing**, all
  offline. Docker tests only run when the stack is up.

## 4. Doc reconciliation (part of this work)
- `CLAUDE.md`: change the vector-store references from hnswlib → **ChromaDB (service)**; note Postgres
  is relational-only (no pgvector); remove the "conftest mocks ChromaDB — spec is hnswlib" caveat.
- `docs/NOVA_AI_MASTER_ARCHITECTURE.md`: same vector-store update in the Infrastructure/Storage
  sections; add an "Infra substrate" note pointing at this increment.
- Per-layer docs that name hnswlib (Layer 2) get a one-line as-built correction.

## 5. Success criteria
1. `pytest tests/` green and fully offline (1120 existing + new offline unit tests).
2. `python -c "from config import load_config; c = load_config(); print(c['llm']['system2']['provider'])"` prints `groq`; setting `system2.provider: ollama` in an override flips it.
3. `build_llm_clients(load_config())` returns three concrete clients of the configured provider types (verified with patched SDKs offline).
4. `docker compose up -d` brings up all five services healthy; the Docker integration tests pass against them.
5. Docs no longer reference hnswlib/pgvector as the vector path; ChromaDB is authoritative.

## 6. Explicit non-goals (follow-up increments)
`api/` FastAPI app + routes · `background/` scheduler + jobs · `scripts/` CLIs · Alembic migrations ·
`infra/websocket/` · `infra/session_cache.py` · wiring the real infra into a live `run_turn` end to end
(that lands with `api/`).
