# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nova AI is a **13-layer cognitive architecture** for long-term human-AI companionship. It is not a chatbot — it is a system designed to accumulate context, continuity, emotional understanding, and relational depth across years of interaction.

**Implementation status:** all 13 layers are implemented, tested, documented, and wired together through the conversation orchestrator (130 layer modules + 6 pipeline modules; **1120 tests passing** — `/usr/bin/python3.11 -m pytest tests/ -q`). The code is pure-stdlib and dependency-injected so the whole suite runs offline with no model servers or databases; production swaps concrete backends behind the same interfaces. **`docs/NOVA_AI_MASTER_ARCHITECTURE.md` is the canonical top-level single source of truth** — read it first; per-layer detail lives in `docs/layer-N-architecture.md` (each with an as-built section). When code and any doc disagree, the code wins.

## Commands

```bash
# Start all infrastructure (Ollama, Kokoro TTS, and backing services)
docker compose up -d

# Run development API server
uvicorn api.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/path/to/test_file.py

# Run a single test by name
pytest tests/path/to/test_file.py::test_function_name -v

# Apply DB migrations (production/persistent Postgres; the test suite uses create_all)
alembic upgrade head

# Seed the database with sample data
python scripts/seed_db.py

# Run memory recall evaluation
python scripts/eval_recall.py

# Export audit trail
python scripts/export_audit.py

# Calibrate recall weights
python scripts/calibrate_weights.py
```

Configuration loads `config/defaults.yaml` first, then overrides with layer-specific `config/layerN.yaml` files. Example config keys: `llm.groq_model`, `llm.ollama_system1_model`, `memory.recall_weights`, `memory.decay_rate`.

## Architecture: The 13-Layer Cognitive Pipeline

The pipeline flows sequentially through layers on each conversation turn. `backend/pipeline/conversation_orchestrator.py` is the entry point — it sequences all layers and is the most important file to understand.

### Dual-Pipeline Routing (System 1 / System 2)

After Layer 3 classifies message complexity, traffic routes to one of two pipelines:

- **System 1** (`backend/pipeline/system1_pipeline.py`): Fast path (<2s). Uses **Ollama + qwen2.5:7b** for casual/banter responses. Skips the Emotion Refiner (Agent 4b).
- **System 2** (`backend/pipeline/system2_pipeline.py`): Full path (<30s). Uses **Groq API + llama-3.3-70b-versatile** for complex/emotional messages. Runs both Semantic Planner (Agent 4a) and Emotion Refiner (Agent 4b).

Note: Layer 3 uses a separate fast classification model (**Phi-3 Mini 3.8B or Gemma 2B**) purely for emotion + intent classification — this runs on every message regardless of System 1/2 routing.

### Layer Map

| # | Module | Role |
|---|---|---|
| 1 | `backend/layer1_input/` | Input perception: temporal context (circadian bands, session gap), implicit behavioral signals (latency, deletion, message length), multimodal normalization, voice prosody |
| 2 | `backend/layer2_memory/` | Memory arbiter: STM buffer, Episodic/Semantic/Identity stores, User World Model, recall scoring, forgetting & consolidation, audit trail |
| 3 | `backend/layer3_reasoning/` | Emotion + intent classification (shared LLM call), Background Emotional State, stated-vs-felt mismatch detection, Empathy Hypothesis, conversation mode resolution |
| 4 | `backend/layer4_persona/` | Persona State Resolver, Relationship State Manager, tone calibration, Drift Detector, Semantic Planner (Agent 4a), Emotion Refiner (Agent 4b) |
| 5 | `backend/layer5_relationship/` | Social Graph, interpersonal event tracking, social pattern recognition, coaching opportunity detection and injection |
| 6 | `backend/layer6_proactivity/` | Proactive queue, timing & delivery gates, proactive message generation, response tracking |
| 7 | `backend/layer7_goals/` | Goal extraction from natural language, goal lifecycle, progress monitoring, accountability injection, goal decomposition + Layer 6 handoff |
| 8 | `backend/layer8_tools/` | Tool Use & Actions: tool manager (intent→resolve→confirm→execute→record), confirmation gate (AUTO/SOFT/HARD), parameter resolver (one question/turn), append-only action recorder, and swappable plugins (calendar, email, web search, reminders, notes). Crisis/safety is **not** here — it lives in Layer 11. |
| 9 | `backend/layer9_output/` | Output delivery: format adaptation, micro-interaction engine (typing simulation, thinking pauses, self-editing), voice synthesis via Kokoro TTS (SSML), streaming |
| 10 | `backend/layer10_longitudinal/` | Life Narrative Engine, Weekly Summary Engine, Progress & Pattern Tracker, Retrospective Engine, Life Calendar |
| 11 | `backend/layer11_safety/` | Safety Agent: SC-2 (Crisis Detection) runs **in parallel** with every message; SC-1 (Ethical Guardrails) runs **post-generation** on every response; SC-4 (Dependency Monitor) runs weekly. SC-3 (Escalation Protocol) has veto authority — discards normal response and replaces it entirely when crisis is detected. |
| 12 | `backend/layer12_privacy/` | On-device SQLCipher databases, AES-256-GCM vector store, selective deletion with cascade handling, memory audit (tamper-evident hash chain), zero-knowledge cloud sync |
| 13 | `backend/layer13_onboarding/` | Cold Start Engine (temporary overlay): progressive elicitation, initial defaults, feature pacing controller. Self-terminates on graduation criteria. |

**Key pipeline ordering details:**
- Layer 11 Safety Agent (SC-2) runs in parallel with the main pipeline — it is never blocked or delayed
- Layer 11 SC-1 (Ethical Guardrails) runs post-generation, before Layer 9 delivers output
- Layer 13 constraints are applied early (after Layer 2) during onboarding period
- All responses — System 1, System 2, crisis or normal — pass through Layer 9 before delivery

### Memory System (Layer 2)

Eight sub-components organized in three groups:

**Storage sub-components:**
- **Short-Term Memory (STM)**: In-RAM session buffer; 40-turn rolling window, 12,000-char limit; never persisted; evicted turns pass through a promotion check before discard
- **Episodic Memory**: Summaries of meaningful past interactions; embeddings stored in **ChromaDB** (`episodic_memory` collection, cosine space) via the Ollama `nomic-embed-text` embedding function; embedding dim follows the model. (Historical note: earlier revisions specified hnswlib/`memory.vdb`; superseded by the ChromaDB infra substrate — see `infra/vector_store/`.)
- **Semantic Memory**: Stable generalized facts distilled from clustered episodic memories by the FCE; `confidence` increases with each supporting episode
- **Identity Memory**: Nova's self-model (beliefs, values, behavioral policies); some entries are `is_immutable = True` (safety-critical, never updated)
- **User World Model (UWM)**: Structured model of the user as a person in the world — profile, relationship graph, life context, psychological model, communication model. **On-device only, never cloud-synced.** The most sensitive data structure in the system.

**Processing sub-components:**
- **Recall Scoring Engine**: 4-signal competitive recall formula: `RecallScore = α·Semantic + β·Emotional + γ·Temporal + δ·Importance` with default weights α=0.40, β=0.30, γ=0.20, δ=0.10. Uses softmax temperature τ (default 0.7, dynamic per context mode). Maximum 3 memories returned per call.
- **Forgetting & Consolidation Engine (FCE)**: Background job. Triggered when: ≥50 new episodes since last run, ≥25 sessions elapsed, or 14 days have passed. Runs decay sweep → cluster detection (agglomerative, cosine threshold 0.85) → semantic extraction. Not the same as the scheduler's `memory_consolidation_job` (which runs every 2 hours).
- **Memory Audit Trail**: Append-only log with SHA-256 hash chain (tamper-evident). Every memory lifecycle event is logged with reason and triggering agent.

**Memory mood-congruent recall**: The emotional component (β=0.30) implements mood-congruent recall — when a user is distressed, memories formed during past distress score higher. This is a first-class architectural design decision, not a filter.

**Write separation**: All memory writes go through the State Updater which runs **after** the conversation turn completes. Layer 2 is read-only during inference — memory cannot be mutated mid-response.

### Layer 3 Classification Details

SC-1 (Emotion Classifier) and SC-3 (Intent Classifier) **share a single LLM call** to a fast small model (Phi-3 Mini 3.8B or Gemma 2B). Both outputs are returned in one JSON response. The shared LLM call target is <150ms.

The conversation mode (one of: `crisis`, `emotional_support`, `celebration`, `technical_discussion`, `goal_planning`, `social_coaching`, `life_review`, `casual`) is resolved deterministically from classification outputs and governs Layer 2 context gating, Layer 4 generation constraints, and Layer 9 pacing.

When `crisis_flag=True` (confidence > 0.65), Layer 3 immediately emits a CrisisAlert to **Layer 11 (Safety Agent)** — this does not wait for the EmotionIntentPacket to complete. Layer 11's SC-2 (Crisis Detection Engine) runs its deeper 3-layer detection in parallel with the main pipeline and has final veto authority; SC-3 (Escalation Protocol) replaces the normal response when a crisis is confirmed. See `docs/layer-11-architecture.md` for the full crisis-handling spec. (Note: crisis/safety is owned by Layer 11, not Layer 8 — Layer 8 is Tool Use & Actions.)

### Layer 4 Two-Stage Generation

- **Agent 4a (Semantic Planner)**: Generates factually complete response content. Does NOT add emotional language — that is explicitly Agent 4b's job. Constrained by advice gate (`open`/`gated`/`closed`) from Layer 3.
- **Agent 4b (Emotion Refiner)**: Takes the semantic draft and adjusts tone, warmth, validation sequencing, and phrasing without changing factual content. Skipped entirely when all 5 neutral conditions are true (no emotional stakes). Post-refinement factual validation uses embedding cosine similarity to check key claims were preserved.

Architecture docs recommend Phi-3 Medium (14B) / Gemma 2 9B for Agent 4a, and Llama 3.1 8B / Gemma 2 9B Instruct for Agent 4b. The config/pipeline uses Groq API (llama-3.3-70b) for System 2 overall — the per-agent model assignments are aspirational targets in the architecture docs.

### API Layer (`api/`)

The HTTP surface is live for conversation + health. `uvicorn api.main:app` boots the app; its
lifespan builds the `AppState` composition root (`api/state.py`: config → `infra` LLM clients →
Postgres engine + `init_db` → Chroma store → `ConversationOrchestrator`). Endpoints:
- **`POST /chat`** (`ChatRequest{message, session_id?}` → `ChatResponse`): drives one
  `orchestrator.run_turn`. **Sync `def` on purpose** — FastAPI runs it in a worker thread so
  `api/assembly.py`'s async→sync bridge (`_run`) is safe (Layers 1 & 2 are `async`; the orchestrator
  is sync).
- **`POST /chat/stream`** (`ChatRequest` → `text/event-stream`): the same full turn, streamed as
  Server-Sent Events (`meta` → `token`×N → `done`), paced by Layer 9's `StreamTypingOverlay`
  (`api/streaming.py`). **Not** token-from-LLM: the whole turn (crisis veto + SC-1 + post-turn
  writes) runs first, then the *delivered, guardrailed* text is replayed as paced token frames —
  honoring the invariant that SC-1 runs before Layer 9 delivers. Tokens concatenate losslessly to
  the delivered text. Sync generator ⇒ Starlette iterates it in the threadpool (bridge stays safe).
  See `docs/superpowers/specs/2026-07-06-chat-streaming-and-full-integration-design.md`.
- **`GET /health`** (liveness; compose healthcheck) and **`GET /health/ready`** (probes Postgres).
- **Read surface over persisted state** (single-user, no auth; `api/routes/`): `GET /goals`
  (+`?status=`), `GET /goals/{id}`, `POST /goals`; `GET /memory/audit`, `GET /memory/{id}`;
  `GET /safety/events`; `GET /onboarding`; `GET /sessions`. Each builds the relevant Postgres store
  from `state.session_factory`+`default_user_id`; a `POST /chat` turn's writes are readable back
  through these (see `docs/superpowers/specs/2026-07-05-api-read-surface-design.md`).
- **Privacy (Layer 12)** (`api/routes/memory.py`): `DELETE /memory/{id}` runs the real Layer-12
  single-memory selective deletion — a genuine "forget" (logical `is_deleted` + embedding/content
  zeroed so it can never be recalled again, row retained for proof), returning a signed
  `DeletionCertificate` and appending a tamper-evident entry to the **`PostgresPrivacyAudit`** SHA-256
  chain (`infra/db/privacy_audit.py` → `privacy_audit` table). `GET /memory/integrity` verifies both
  the Layer-2 memory-audit chain and the Layer-12 privacy chain. (Cross-store semantic/personality/
  longitudinal cascade is a documented follow-up — Layer-12's cascade schema differs from Layer-2's.)
- **Relationship + goal accountability (Layer 4/5/7 → generation)** (`api/routes/relationship.py`):
  `GET /relationship` reads the per-user Layer-4/5 relationship state (`PostgresRelationshipStore` →
  `relationship_state` JSONB). Every `/chat` turn advances it (`make_relationship_writer.record_turn`:
  message/session counters + qualitative `stage` on the architecture's session thresholds new→…→close)
  and feeds it back into generation: `build_persona` turns the stage into a plain-language familiarity
  directive on the `PersonaPacket.persona_instruction`, and the `plan` adapter injects a **goal
  accountability** directive (relevant active goal titles from `PostgresGoalStore.get_relevant_goals`
  via `make_goal_provider`) through the planner's `response_instruction` — both reach
  `build_planner_prompt`, honoring the "plain-language directives, no raw scores" invariant.
- **Proactivity + Longitudinal + Admin** (`api/routes/{proactive,longitudinal,admin}.py`):
  `GET /proactive` polls the Layer-6 outreach queue (top pending candidates; no push channel without
  a frontend), `GET /longitudinal/summaries` + `GET /longitudinal/latest` read Layer-10 weekly
  summaries, and `POST /admin/jobs/{name}` runs any background job on demand (single-user, no auth).
  The five jobs (`background/*.py`, registry in `background/scheduler.py`) are plain
  `run(app_state) -> dict` callables operating on the persisted stores: `integrity_check` (verify
  both hash chains), `memory_consolidation` (Layer-2 `decay_sweep` + persist), `proactive_check`
  (queue recompute/expire, suppressed while cold-starting), `longitudinal_summary` (generate + persist
  a `WeeklySummary`), `pattern_detection`. `start_scheduler` runs them in-process via APScheduler,
  **opt-in through `config.scheduler.enabled`** (lazy-imported so the offline gate never needs it;
  no-op if disabled/absent), started/stopped in the app lifespan.
- **Sync (Layer 12, zero-knowledge)** (`api/routes/sync.py`): `POST /sync/push`, `GET /sync/pull`,
  `GET /sync/status`. The server is a **blind relay** — it stores opaque AES ciphertext produced
  on-device by `SyncCoordinator.build_delta` (`PostgresSyncStore` → `sync_delta` table) and hands
  each device the deltas from *other* devices past its cursor (the monotonic row `id`). It never
  holds the key and never decrypts; `push` is idempotent on `delta_id`.
- **Tools (Layer 8)** (`api/routes/tools.py`): `GET /tools/pending`, `POST /tools/confirm/{id}`,
  `POST /tools/deny/{id}`, `GET /tools/history`. A single `ToolManager` lives on `AppState`
  (`build_tool_manager`) with the five plugins registered against **local/offline backends** (no
  third-party creds) and a durable **`PostgresActionRecorder`** (`infra/db/action_recorder.py` →
  `tool_action` JSONB). The `/chat` pipeline runs Layer 8 **before generation** via the orchestrator's
  `tool_use` hook: a detected intent short-circuits generation with a clarification question, a
  confirmation prompt, or an executed result; SOFT/HARD actions register a pending token confirmable
  on a later request through `/tools/confirm`. `ChatResponse.tool_invoked` flags a tool turn.

`api/assembly.py` is the adapter layer mapping **all 12** `PipelineSteps` hooks onto real
layer entrypoints — every `/chat` turn now exercises all 13 layers. SC-1 `guardrails` run
post-generation (adapter maps `EthicalGuardrailResult.final_response` onto `approved`/`replacement`,
so any block/modification is applied before Layer 9 delivers). The Layer-13 `cold_start` overlay is
persisted-state-driven (`make_cold_start_provider` reads `PostgresOnboardingStore`): observe-only /
drift-gated directives while cold-starting, `None` once graduated (self-terminating). Single-user:
`user_id` = `config['system']['default_user_id']` (env `NOVA_USER_ID`).
The live recall path retrieves Layer-2 candidates by **ChromaDB ANN** when a vector store is present:
`recall` wraps `PostgresMemoryStore` in **`AnnRecallStore`** (`infra/db/ann_recall_store.py`) bound to
the query embedding — it asks Chroma for the nearest episodic neighbours and hydrates them from
Postgres, degrading to the linear candidate scan when the index is cold or the vector store is
unavailable. **Recall passes the raw `user_id`** (not a uuid5) so it matches the write path + read
routes (a prior uuid5 mismatch meant persisted episodes were never recalled — now fixed).
The post-turn writer runs the **real Layer-2 `state_updater`** (`make_state_update_writer`):
it persists a new `EpisodicMemory` (JSONB payload + embedding, via `infra/db/memory_serde.py`) **and
indexes its embedding into Chroma** for the ANN path (deletion drops it from the index too),
reinforces the recalled memories the response actually reflected (similarity-gated `S_current`
write-back), bumps the UWM version if present, appends a durable SHA-256 audit chain
(**`PostgresAuditTrail`**, `infra/db/audit_trail.py`, continues across restarts), and upserts a
`Session` turn row — so `/chat` both remembers and strengthens memories across restarts. The post-turn
path also runs the **real Layer-7 goal pipeline** (`make_goal_writer` → `run_goal_pipeline` against
`PostgresGoalStore`, `infra/db/goal_store.py`), extracting and persisting stated goals, and appends the
turn's crisis assessment to an append-only safety log (`make_safety_writer` → `PostgresSafetyLog`,
`infra/db/safety_store.py`), and advances a self-graduating onboarding session counter
(`make_onboarding_writer` → `PostgresOnboardingStore`, `infra/db/onboarding_store.py`) — all writers
composed via `_chain_writers`. See `docs/superpowers/specs/2026-07-05-postgres-memory-store-design.md`,
`docs/superpowers/specs/2026-07-05-layer2-write-path-persistence-design.md`, and
`docs/superpowers/specs/2026-07-05-goal-persistence-design.md`. **Not yet wired (documented
follow-ups):** auth/multi-user, WebSocket transport for streaming (SSE is live; WS is the future
bidirectional upgrade), the full Layer-13 elicitation/feature-pacing machinery (the cold-start
overlay reads persisted graduation state but does not yet run per-turn elicitation — needs a
persisted session_context) and per-user Layer 4/5 persona-param *learning* (relationship
progression is wired; persona warmth/verbosity learning is not). See
`docs/superpowers/specs/2026-07-04-api-conversation-endpoint-design.md`
§8 and `docs/superpowers/specs/2026-07-06-chat-streaming-and-full-integration-design.md` for the
full roadmap.

### Infrastructure Stack

- **API**: FastAPI + WebSockets (`api/main.py`)
- **Relational DB**: PostgreSQL (runs as its own container) — the structured/relational store for per-layer state via SQLAlchemy 2.x (`infra/db/`). Vectors live in ChromaDB, so no pgvector is used. The persistent schema is managed by **Alembic** (`alembic upgrade head`; baseline `migrations/versions/0001_baseline_schema.py` runs `create_all`); `init_db`/`create_all` remains the fast path for the offline SQLite test suite and ad-hoc bootstrap.
- **On-device DB**: SQLite + SQLCipher (encrypted at rest) for user-sensitive data (UWM, audit trail, goals, personality, safety records) owned by Layer 12
- **Vector store**: **ChromaDB** (runs as its own service/container; `infra/vector_store/`) — embeddings via the Ollama `nomic-embed-text` embedding function, cosine space, collections `episodic`/`semantic`/`identity`. Supersedes the earlier hnswlib design. Note: `conftest.py` still mocks a vector store for offline unit tests; the production store is ChromaDB. See `docs/superpowers/specs/2026-07-04-infra-runtime-substrate-design.md`.
- **Local LLM inference**: Ollama serving qwen2.5:7b (System 1), gemma3:4b, nomic-embed-text (embeddings)
- **Cloud LLM**: Groq API (llama-3.3-70b-versatile) for System 2
- **Layer 3 classifier**: Phi-3 Mini / Gemma 2B (emotion+intent classification, fast path)
- **TTS**: Kokoro (custom Docker image on port 8880, OpenAI-compatible API)
- **Background Jobs**: APScheduler via `background/scheduler.py` — memory consolidation (every 2h), proactive checks (every 30min), pattern detection (weekly), integrity checks (daily), longitudinal summaries (weekly). **Implemented + wired**: each job is a `run(app_state)` callable over the Postgres stores, registered in `scheduler.JOBS`, run in-process **opt-in via `config.scheduler.enabled`** (APScheduler lazy-imported so the offline gate never needs it), and individually runnable via `POST /admin/jobs/{name}`.
- **Session Cache**: `infra/session_cache.py` — ephemeral per-turn in-memory buffer holding intermediate layer outputs. Distinct from Layer 2's Short-Term Memory Buffer.

### Docker Services

Topology lives in `docker/docker-compose.yml` (compose file + per-service Dockerfiles under `docker/`). Bring the backing services up with `docker compose -f docker/docker-compose.yml up -d`; the `backend` app container is gated behind the `app` profile until the `api/` layer exists.

```
postgres → port 5432 (relational store; loopback-bound)
chroma   → port 8001→8000 (vector store; loopback-bound)
ollama   → port 11434 (local LLM inference; pulls qwen2.5:7b, gemma3:4b, nomic-embed-text on first start)
kokoro   → port 8880 (TTS)
backend  → port 8000 (FastAPI; profile `app`)
```

All published ports bind to `127.0.0.1` only (no LAN exposure of Postgres/Chroma/Ollama); the backend runs as a non-root user. `backend` depends on postgres/chroma/ollama being healthy before starting. All services on the `nova-network` bridge network.

## Key Design Invariants

- **Fuzzy temporal labels only**: The LLM never sees raw ISO timestamps. Layer 1's `fuzzy_label_for_timestamp` utility converts all timestamps to human-relative language ("a few weeks ago"). This is enforced in Layer 4's prompt construction.
- **No raw scores to LLM**: Valence/arousal floats, recall scores, crisis_confidence, and BES label scores are never passed to the LLM as numbers. Layer 3 converts them to plain-language directives (`response_instruction`, `emotional_posture_instruction`).
- **Memory writes are non-destructive**: Deletions are logical (`is_deprecated`/`is_archived` flags). Old versions retained in audit trail. User World Model node deletions are cascaded to related events/patterns.
- **Layer 9 always runs**: Every response passes through Layer 9 interaction orchestration before delivery.
- **Confabulation guard**: When `recalled_memories = []`, the downstream prompt must include an explicit instruction not to invent or imply specific memories.
- **Test isolation**: Tests use in-memory SQLite with per-test rollback and mock LLM clients (see `tests/conftest.py`).

## Layer 8 / Layer 11 (resolved)

A prior revision of `docs/layer-8-architecture.md` mislabeled Layer 8 as a "Crisis Detection & Safety Engine" — a layer-numbering mismatch. This is now resolved: **Layer 8 is Tool Use & Actions** (`backend/layer8_tools/`), and **crisis/safety is owned entirely by Layer 11** (`backend/layer11_safety/`, `docs/layer-11-architecture.md`: Ethical Guardrails, Crisis Detection Engine, Escalation Protocol, Dependency Monitor). The Layer 8 architecture doc has been rewritten to specify the tools layer; the prior crisis text remains recoverable in git history.
