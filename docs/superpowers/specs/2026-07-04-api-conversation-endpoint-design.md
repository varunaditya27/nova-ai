# API Conversation Endpoint — Design Spec

**Date:** 2026-07-04
**Status:** Approved (design), pending implementation plan
**Scope:** Build the `api/` FastAPI app that wires the real `infra/` substrate into a live
`ConversationOrchestrator.run_turn`, exposing `POST /chat` and `GET /health`. This is the increment
that makes Nova a running service and activates the dockerised `backend` container (`app` profile).

---

## 1. Motivation

The 13 cognitive layers, the pipeline orchestrator, and the `infra/` substrate (config, LLM clients,
ChromaDB, Postgres) are all implemented and tested. What is missing is the HTTP surface that boots the
substrate and drives a real conversation turn. `api/` is comment-only scaffolding today, so
`uvicorn api.main:app` does not start. This increment delivers a working `/chat` endpoint and the
`/health` check the compose `backend` service needs.

## 2. Design decisions (approved)

| Decision | Choice |
|---|---|
| Adapter fidelity | Wire real layers via an assembly module; faithful thin adapters where a layer needs heavy sub-dependency construction. |
| Route scope | `POST /chat` + `GET /health` (+ `GET /health/ready`) only. |
| Auth | Single-user, no auth; `user_id` from `system.default_user_id` (env `NOVA_USER_ID`). |
| Chat transport | REST JSON (request/response). WebSocket streaming deferred. |
| Persistence | Post-turn `state_update` writes a real Postgres turn record (session + episodic). Layer-2-store↔ORM bridge and Chroma live-path write deferred (see §8). |
| Deps | New `api` extra in `pyproject.toml` (`fastapi`, `uvicorn[standard]`). |

## 3. Components (all under `api/`)

### 3.1 `api/state.py`
`AppState` dataclass holding the booted substrate: `config: dict`, `llm_clients: dict`,
`engine`, `session_factory`, `vector_store`, `orchestrator: ConversationOrchestrator`,
`default_user_id: str`. Constructed once at startup, disposed at shutdown.
- `build_app_state(config: dict | None = None) -> AppState` — the composition root: `load_config()`,
  `build_llm_clients(config)`, `make_engine(config['system']['database_url'])` + `init_db(engine)` +
  `make_session_factory`, `build_vector_store(config)`, `build_pipeline_steps(...)`, and
  `ConversationOrchestrator(steps)`.

### 3.2 `api/assembly.py` — the adapter layer (the crux)
`build_pipeline_steps(*, llm_clients, session_factory, vector_store, config) -> PipelineSteps`.
Each of the 12 `PipelineSteps` hooks is a thin adapter that translates `TurnContext` ↔ the layer's
real packet type and calls its real entrypoint:

| Hook | Real layer entrypoint | Notes |
|---|---|---|
| `perceive` | `backend.layer1_input.process_input_event` | build `InputPerceptionPacket`; in-memory temporal/behavior profiles this increment |
| `recall` | `backend.layer2_memory.memory_arbiter` | in-process memory store + injected embedder (fake offline / Ollama live) |
| `cold_start` | `backend.layer13_onboarding.ColdStartEngine` | one engine instance per user (in-memory state this increment) |
| `classify` | `backend.layer3_reasoning.build_emotion_intent_packet` | injected classifier LLM (system1 client) |
| `safety_scan` | `backend.layer11_safety.SafetyAgent` (SC-2) | crisis detection; never blocked |
| `build_persona` | `backend.layer4_persona.assemble_persona_packet` | |
| `plan` | `backend.layer4_persona.generate_semantic_draft` | injected system1/system2 client per route |
| `refine` | `backend.layer4_persona` emotion refiner | system2 client |
| `guardrails` | `backend.layer11_safety.run_all_checks` (SC-1) | post-generation |
| `escalate` | `backend.layer11_safety.generate_crisis_response` (SC-3) | replaces output on crisis |
| `deliver` | `backend.layer9_output.deliver` | format/pacing; SSML/voice not exercised over REST |
| `state_update` | `api` writer → `backend.layer2_memory.state_updater` + Postgres write | see §3.3 |

Adapters that need a store use Layer 2's `InMemoryMemoryStore` and Layer 13's in-memory state for this
increment (behaviourally real, not yet DB-persisted — see §8). Every LLM-touching adapter calls a real
`infra` `LLMClient`, so a live `/chat` needs Ollama/Groq; offline tests inject fake clients.

### 3.3 Persistence (this increment)
The post-turn `state_update` adapter opens a `session_scope(session_factory)` and writes a real
Postgres `Session` (upsert turn_count) + `EpisodicMemory` row for the turn. This proves the relational
path end-to-end. Failures are logged and swallowed (post-turn writes never affect the delivered
response — matches the orchestrator invariant).

### 3.4 `api/schemas.py`
Pydantic models: `ChatRequest {message: str, session_id: str | None = None}`;
`ChatResponse {response: str, conversation_mode: str, cognitive_system: str, crisis_active: bool,
refined: bool, session_id: str}`.

### 3.5 `api/routes/chat.py`
`POST /chat` → resolve orchestrator via `Depends(get_orchestrator)` → `run_turn(default_user_id,
req.message, session_id=req.session_id or generated)` → map `OrchestratedOutput` → `ChatResponse`.
Errors → 503 with a safe message (never leak internals).

### 3.6 `api/routes/health.py`
- `GET /health` — liveness, always `{"status": "ok"}` (compose healthcheck target).
- `GET /health/ready` — readiness: probe Postgres (`SELECT 1`) and Chroma heartbeat with short
  timeouts; `200 {"status":"ready", ...}` or `503` with the failing component. Never probes LLMs
  (readiness must not depend on model warmup).

### 3.7 `api/main.py`
`create_app() -> FastAPI` with an async lifespan that calls `build_app_state()` on startup (stashed on
`app.state`) and disposes the engine on shutdown; CORS for `config['api']['cors_origins']`; includes
the chat + health routers; installs the logging middleware. Module exposes `app = create_app()` so
`uvicorn api.main:app` works.

### 3.8 `api/dependencies.py` / `api/middleware/logging.py`
`get_state(request) -> AppState` (from `request.app.state`), `get_orchestrator(state)`.
Logging middleware records method, path, status, and duration (no request bodies — may contain PII).

### 3.9 Config additions (`config/defaults.yaml`)
```yaml
system:
  default_user_id: ${NOVA_USER_ID:-local-user}
api:
  host: ${API_HOST:-0.0.0.0}
  port: ${API_PORT:-8000}
  cors_origins: ["http://localhost:3000"]
```

### 3.10 Deps & Docker
`pyproject.toml`: `api = ["fastapi>=0.110", "uvicorn[standard]>=0.29"]`; `dev` includes it.
`docker/Dockerfile`: install `.[infra,api]`. The `backend` service (profile `app`) now serves.

## 4. Data flow (a turn)
`POST /chat {message}` → chat route → `orchestrator.run_turn(user_id, message, session_id)` →
[L11 safety scan → L1 perceive → L2 recall → L13 cold-start → L3 classify → crisis veto? →
route S1/S2 → L4 plan(+refine) → L11 guardrails → L9 deliver → post-turn state_update (Postgres
write)] → `OrchestratedOutput` → `ChatResponse` JSON.

## 5. Testing
- **Offline unit** (`tests/unit/api/`, `importorskip("fastapi")`):
  - `test_health.py` — `/health` 200; `/health/ready` 200 when probes patched healthy, 503 when a
    probe fails.
  - `test_chat.py` — `/chat` 200 + `ChatResponse` shape with the orchestrator dependency-overridden to
    a fake returning a canned `OrchestratedOutput`; 503 when the fake raises.
- **Offline assembly turn** (`tests/unit/api/test_assembly_turn.py`, the fidelity linchpin):
  `build_pipeline_steps` with **fake LLM clients + in-memory stores + in-memory session_factory**
  (SQLite), run a real turn through `ConversationOrchestrator`; assert non-empty response, System 1
  routing for a casual message, confabulation guard on empty recall, and that a Postgres/SQLite turn
  row was written. Exercises the real layer pipeline offline.
- **Docker** (`tests/integration_infra/test_api_health.py`, `@pytest.mark.docker`, auto-skip):
  GET `/health` on the live `backend` container when the `app` profile is up.
- **Invariant:** `pytest tests/` stays green and offline whether or not the `api`/`infra` extras are
  installed (importorskip guards).

## 6. Success criteria
1. `uvicorn api.main:app` starts against the dockerised stack; `GET /health` → 200.
2. `POST /chat {"message":"hey"}` returns a `ChatResponse` with non-empty `response` (live: real
   Ollama System 1; offline test: fake client) and a Postgres turn row is written.
3. `docker compose -f docker/docker-compose.yml --profile app up` builds and runs `backend` healthy.
4. Offline suite green with new api unit + assembly tests; docker/api tests skip offline.

## 7. Non-goals (this increment)
Auth/users · other routes (goals/memory/sync/tools) · WebSocket streaming · Layer-2-store↔ORM
persistence bridge · Chroma embedding writes in the live path · background scheduler · voice/SSML over
the wire.

## 8. Future Scope / Roadmap (post-`api/`)

The following remain to reach a fully production-complete Nova. Each is independently shippable via the
same brainstorm → spec → plan → TDD flow, roughly in priority order.

**A. Persistence completion (highest priority follow-up)**
- **Layer-2-store↔ORM bridge:** a `PostgresMemoryStore` / `ChromaBackedVectorIndex` implementing Layer
  2's store & `VectorIndex` protocols, so episodic/semantic memories persist to Postgres + Chroma
  across restarts (replaces the in-process store used in `/chat` now). Embedding writes to Chroma in
  the live recall/write path.
- **Per-user state persistence:** persist Layer 4 persona, Layer 5 relationship, Layer 7 goals, Layer
  13 onboarding, Layer 11 safety records to their ORM tables (models already exist) via State Updater
  writers; load them at turn start instead of in-memory defaults.
- **Alembic migrations:** replace `init_db`/`create_all` with versioned migrations.

**B. API surface expansion**
- Remaining routes: `memory` (recall/inspect), `goals` (CRUD), `tools` (Layer 8 execute/confirm),
  `sync` (Layer 12 multi-device), `auth`.
- **WebSocket `/chat/stream`:** stream tokens + Layer 9 micro-interaction events (typing, thinking
  pauses, self-edits); voice/SSML via Kokoro over the socket.
- **Auth & multi-user:** JWT accounts, hashed passwords, a `users` table, per-user scoping across all
  layers; rate limiting.

**C. Background jobs (`background/`)**
- APScheduler wiring + the jobs: `memory_consolidation_job` (2h, Layer 2 FCE), `proactive` check
  (30m, Layer 6 — currently suppressed during cold start), `pattern_detection` (weekly, Layer 5/10),
  `integrity_check` (daily, Layer 12), `longitudinal_summary` (weekly, Layer 10). Wire the proactive
  pipeline to real delivery.

**D. Utility scripts (`scripts/`)**
- `seed_db`, `eval_recall`, `export_audit`, `calibrate_weights` (documented in CLAUDE.md; currently
  comment-only).

**E. Infra hardening**
- `infra/session_cache.py` (ephemeral per-turn buffer) and `infra/websocket/` (connection manager +
  event emitter) for the streaming path.
- Production secrets management (replace dev Postgres creds; authenticated gateway in front of
  Chroma/Ollama instead of publishing ports); TLS.
- Observability: structured logging, metrics, tracing across the pipeline.

**F. Model/quality**
- Wire the Layer 3 fast classifier to a dedicated small model (Phi-3 Mini / Gemma 2B) instead of the
  System 1 client; realise the aspirational Agent 4a/4b model assignments.
- Recall weight calibration (`scripts/calibrate_weights.py`) against real usage; eval harness.

**G. Frontend**
- The `localhost:3000` client the CORS config anticipates (out of scope for this repo's backend work,
  noted for completeness).
