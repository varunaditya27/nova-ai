# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nova AI is a **13-layer cognitive architecture** for long-term human-AI companionship. It is not a chatbot — it is a system designed to accumulate context, continuity, emotional understanding, and relational depth across years of interaction.

**Implementation status:** all 13 layers implemented and wired through the conversation orchestrator (130 layer modules + 6 pipeline modules). **1573 tests passing** — run with `.venv/bin/pytest` (or any interpreter with the project's deps; `tests/unit/api/` needs SQLAlchemy on the path). 40+ routes live — see `docs/API_REFERENCE.md`. Layer code is pure-stdlib and dependency-injected; production swaps concrete backends behind the same interfaces.

**Docs hierarchy:** `docs/NOVA_AI_MASTER_ARCHITECTURE.md` is the canonical source of truth (read first) → `docs/layer-N-architecture.md` per layer (each ending in a "Live Wiring Status (current state)" section + a dated "Decision Log") → `docs/POLISH_BACKLOG.md` for open follow-ups found during the audit pass (source of truth; `docs/PENDING_WORK.md` is its generated filtered view). **When code and docs disagree, the code wins** — then fix the doc.

## Engineering Principles (strictly enforced)

- **No AI slop.** Don't add abstractions, config knobs, fallback paths, or "for future extensibility" scaffolding beyond what the current task needs. Three similar lines beat a premature helper. A bug fix doesn't need surrounding refactoring.
- **No speculative error handling.** Guard the boundaries that can actually fail (LLM calls, DB reads, backend I/O — this codebase already does this well, e.g. every Layer-1 sub-component degrades gracefully per §11). Don't wrap internal, trusted calls in `try/except` "just in case."
- **Small, verifiable diffs.** Prefer the smallest change that makes the claim true. If you're not sure a piece of code is dead, prove it (grep for callers) before deleting it, and prove a fix works (test + a live run) before calling it done — this file has drifted from the code before (see git history); don't let it happen again.
- **This is a polish project, layer by layer.** We are auditing each of the 13 layers in turn: verify it does what its architecture doc says, cut dead/bloated code, fix what's small and safe, and log everything bigger as a dated entry in `docs/POLISH_BACKLOG.md` instead of fixing it inline. Check that file before starting a layer's audit and before assuming a gap is new.
- **Keep this file lean.** Add facts, not narration. When a finding needs more than 2–3 lines, it belongs in `docs/POLISH_BACKLOG.md` or the relevant `docs/layer-N-architecture.md`'s as-built section — link to it from here instead of inlining it.
- **Wire to the real module, don't reimplement it.** When closing a backlog item, call the existing tested function/class rather than rewriting its logic in the adapter. This audit pass initially flagged three apparent divergent-reimplementation pairs; all three are now resolved — one (sync) turned out to be a correct client/server split, not a duplication, on closer investigation (docs/layer-12-architecture.md); the other two (elicitation surfacing, graduation paths) were genuinely reconciled by wiring the real module in (docs/layer-13-architecture.md). If the real module's shape doesn't fit the call site, that's a sign to fix the call site's contract, not to fork the logic.
- **Every wiring/bug fix needs a test through the real orchestrator or route**, not mocked pipeline steps. Every field-name and dropped-parameter bug found across Layers 4–12 was invisible to mocked-step tests and only surfaced against real object shapes.
- **Closing a backlog item:** mark its bullet `[done]` in `docs/POLISH_BACKLOG.md` with the commit/PR, update the relevant `docs/layer-N-architecture.md` "Live Wiring Status" section, and update CLAUDE.md's one-line layer summary if it no longer holds.

## Commands

```bash
# Start all infrastructure (Ollama, Kokoro TTS, and backing services)
docker compose up -d

# Run development API server
uvicorn api.main:app --reload

# Run the FULL pipeline live (fully offline, all Ollama — no cloud provider, no API key)
#   prereqs: docker services up (incl. kokoro for /voice) + models pulled:
#     `ollama pull qwen2.5:7b gemma2:2b nomic-embed-text`
bash scripts/run_local.sh

# Run all tests
pytest

# Run a single test file
pytest tests/path/to/test_file.py

# Run a single test by name
pytest tests/path/to/test_file.py::test_function_name -v

# Apply DB migrations (production/persistent Postgres; the test suite uses create_all)
alembic upgrade head
```

Configuration loads `config/defaults.yaml` first, then merges all thirteen `config/layerN.yaml` files, then an optional `config/local.yaml` overlay if one exists (`api/state.py::build_app_state`) — useful for local overrides that shouldn't live in defaults, though none ships by default since the platform is fully offline out of the box. Keys actually read by code — `llm.*`, `memory.*`, `onboarding.*`, `scheduler.*`, `system.timezone_offset_hours` (single-user deployment; see `backend/layer1_input/config.py`) — live under `defaults.yaml`. `config/layer1.yaml` is fully consumed (`Layer1Config.from_dict`, threaded through every `backend/layer1_input/` function as an optional `cfg` param — see `docs/layer-1-architecture.md`); `layer2.yaml`–`layer13.yaml` still merge in under their own `layerN:` key but aren't consumed yet (layer code still uses hardcoded constants) — wire each as its layer is revisited, not as one cross-cutting change. See `docs/POLISH_BACKLOG.md`.

## Architecture: The 13-Layer Cognitive Pipeline

The pipeline flows sequentially through layers on each conversation turn. `backend/pipeline/conversation_orchestrator.py` is the entry point — it sequences all layers and is the most important file to understand.

### Dual-Pipeline Routing (System 1 / System 2)

After Layer 3 classifies message complexity, traffic routes to one of two pipelines:

- **System 1** (`backend/pipeline/system1_pipeline.py`): Fast path (<2s). Uses the local **"main" tier** model (`config.llm.system1`, default `qwen2.5:7b` via Ollama, override with `NOVA_MAIN_MODEL`) for casual/banter responses. Skips the Emotion Refiner (Agent 4b).
- **System 2** (`backend/pipeline/system2_pipeline.py`): Full path (<30s). Uses the same **"main" tier** model (`config.llm.system2`) for complex/emotional messages — a different pipeline depth (Semantic Planner + Emotion Refiner both run), not a different model. Fully offline; no cloud provider.

Note: Layer 3's emotion+intent classification (`api/assembly.py::_json_classifier`) and Layer 1's narrative-observation calls both reuse the **System 1 client**, not a separate model — the architecture docs' "Phi-3 Mini / Gemma 2B" classifier is an aspirational per-role target, not what's wired today. Layer-8 tool-intent param extraction is the one call site that does use a distinct **"mini" tier** model (`config.llm.intent`, default `gemma2:2b`, override with `NOVA_MINI_MODEL`).

### Layer Map

| # | Module | Role | Status |
|---|---|---|---|
| 1 | `backend/layer1_input/` | Temporal context, implicit behavioral signals, multimodal normalization, voice prosody | Clean; narrative threads + implicit signals live end-to-end; SC-3/SC-4 correctly unwired (no backend). See `docs/layer-1-architecture.md` as-built section |
| 2 | `backend/layer2_memory/` | Memory arbiter: STM, Episodic/Semantic/Identity stores, User World Model, recall scoring, FCE, audit trail | All 8 sub-components have real production callers, incl. `psychological_model`; STM turns and narrative chains still lack a prompt-side reader. See `docs/layer-2-architecture.md` as-built section |
| 3 | `backend/layer3_reasoning/` | Emotion + intent classification (single shared LLM call), Background Emotional State, mismatch detection, Empathy Hypothesis, mode resolution | Live; two orchestrator wiring bugs fixed during audit; `advice_frustration_count` unforwarded (no counter exists). See `docs/layer-3-architecture.md` as-built section |
| 4 | `backend/layer4_persona/` | Persona State Resolver, Relationship State Manager, tone calibration, Drift Detector, Semantic Planner (4a), Emotion Refiner (4b) | All sub-components live incl. real tie-strength and the critical-drift hard override; style-calibration overwrite is a latent trap once `communication_model` gets wired (see Layer 4 doc). See `docs/layer-4-architecture.md` as-built section |
| 5 | `backend/layer5_relationship/` | Social Graph, event tracking, pattern recognition, coaching detection/injection | Fully built and wired (persistence, per-turn extraction, coaching hook, weekly pattern job); no `SocialEdge` persistence by deliberate decision. See `docs/layer-5-architecture.md` as-built section |
| 6 | `backend/layer6_proactivity/` | Proactive queue, timing & delivery gates, message generation, response tracking, SSE push | Fully live end-to-end incl. real message generation, response tracking, and SSE + frontend consumer. See `docs/layer-6-architecture.md` as-built section |
| 7 | `backend/layer7_goals/` | Goal extraction, lifecycle, progress monitoring, accountability injection, decomposition | Best-wired layer; SC-1..5 all live same-turn or via background jobs; `Goal.deadline` (parsed date) still never populates. See `docs/layer-7-architecture.md` as-built section |
| 8 | `backend/layer8_tools/` | Tool Use & Actions: intent→resolve→confirm→execute→record, 5 plugins. Crisis/safety lives in Layer 11, not here | Cleanest audit — zero bugs, fully wired end-to-end. See `docs/layer-8-architecture.md`'s Live wiring status note |
| 9 | `backend/layer9_output/` | Format adaptation, micro-interaction engine, voice synthesis (Kokoro), streaming | Live incl. persisted format-profile learning and real EMA-computed style signals; `complexity_score`/`turn_type`/`urgency_level`/`voice_mode` have no upstream source yet. See `docs/layer-9-architecture.md` as-built section |
| 10 | `backend/layer10_longitudinal/` | Life Narrative Engine, Weekly Summary, Progress & Pattern Tracker, Retrospective Engine, Life Calendar | Full build complete: chapter synthesis, life calendar, retrospectives, `LifeEvent` detection, Year-in-Review trigger all live. See `docs/layer-10-architecture.md` as-built section |
| 11 | `backend/layer11_safety/` | Safety Agent: Crisis Detection (parallel), Ethical Guardrails (post-gen), Escalation Protocol (veto), Dependency Monitor (weekly) | Cleanest and best-wired layer of the pass — zero bugs, all 4 sub-components live; semantic classifier layer correctly unwired (no model exists). See `docs/layer-11-architecture.md` as-built section |
| 12 | `backend/layer12_privacy/` | On-device encrypted DBs, selective deletion w/ cascade, tamper-evident audit, zero-knowledge sync | Deletion, cascade redaction, and audit/correction views all live; encryption-at-rest is a genuine undeployed infra project, not a wiring gap. See `docs/layer-12-architecture.md` as-built section |
| 13 | `backend/layer13_onboarding/` | Cold Start Engine: progressive elicitation, initial defaults, feature pacing | Full build complete: passive + active elicitation, graduation evaluation all live; `FeaturePacingController` correctly unwired (no feature needs it yet). See `docs/layer-13-architecture.md` as-built section |

**Key pipeline ordering details:**
- Layer 11 Safety Agent (SC-2) runs in parallel with the main pipeline — it is never blocked or delayed
- Layer 11 SC-1 (Ethical Guardrails) runs post-generation, before Layer 9 delivers output
- Layer 13 constraints are applied early (after Layer 2) during onboarding period
- All responses — System 1, System 2, crisis or normal — pass through Layer 9 before delivery

### Memory System (Layer 2)

Eight sub-components organized in three groups:

**Storage sub-components:**
- **Short-Term Memory (STM)**: In-RAM session buffer (`infra/stm_store.py::InProcessSTMStore`, live, LRU-bounded); 100-turn rolling window, 30,000-char limit; never persisted to disk (wiped on restart/LRU eviction, by design); each incoming user turn is promotion-checked immediately on arrival (high arousal, a life-event keyword, or an explicit flag) — real sessions rarely fill the window, so eviction-time checking would never fire and was removed as dead code — before an LLM-summarized episodic memory is created; Nova's own reply text is never eligible; ordinary turns are simply discarded, not persisted verbatim; accumulated turns have no prompt-side reader yet, so in-session "what did I say 3 messages ago" recall is still not live
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

Layer 3 supports an immediate async `alert_fn` push to Layer 11 the moment `crisis_flag=True` (confidence > 0.65), ahead of the full `EmotionIntentPacket` — but `alert_fn` isn't wired live (`api/assembly.py` doesn't pass one; see `docs/POLISH_BACKLOG.md`), so this doesn't fire in production. Crisis safety still works: the orchestrator's crisis veto reads `EmotionIntentPacket.crisis_active` directly (pull, not push) and ORs it with Layer 11's own independent SC-2 scan, which runs its deeper 3-layer detection in parallel with the main pipeline and has final veto authority; SC-3 (Escalation Protocol) replaces the normal response when a crisis is confirmed. See `docs/layer-11-architecture.md` for the full crisis-handling spec. (Note: crisis/safety is owned by Layer 11, not Layer 8 — Layer 8 is Tool Use & Actions.)

### Layer 4 Two-Stage Generation

- **Agent 4a (Semantic Planner)**: Generates factually complete response content. Does NOT add emotional language — that is explicitly Agent 4b's job. Constrained by advice gate (`open`/`gated`/`closed`) from Layer 3.
- **Agent 4b (Emotion Refiner)**: Takes the semantic draft and adjusts tone, warmth, validation sequencing, and phrasing without changing factual content. Skipped entirely when all 5 neutral conditions are true (no emotional stakes). Post-refinement factual validation uses embedding cosine similarity to check key claims were preserved.

Architecture docs recommend Phi-3 Medium (14B) / Gemma 2 9B for Agent 4a, and Llama 3.1 8B / Gemma 2 9B Instruct for Agent 4b. The actual pipeline uses the local "main" tier model (`config.llm.system2`, fully offline via Ollama) for System 2 overall — the per-agent model assignments are aspirational targets in the architecture docs.

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
  The nine jobs (`background/*.py`, registry in `background/scheduler.py`) are plain
  `run(app_state) -> dict` callables operating on the persisted stores: `integrity_check` (verify
  both hash chains), `memory_consolidation` (Layer-2 `decay_sweep`, **plus FCE cluster detection +
  LLM semantic extraction** once enough active episodes accumulate — `save_semantic`/`save_identity`
  are live, not dead code; `should_trigger_fce`'s sessions-/days-since triggers still need a
  persisted "since last run" counter, so only the episode-count trigger fires today), `proactive_check`
  (queue recompute/expire, suppressed while cold-starting), `longitudinal_summary` (generate + persist
  a `WeeklySummary`), `pattern_detection` (Layer-10 SC-3, now persists + hands off to Layer 6 via
  `on_behavioral_pattern`, same re-identification-by-key shape as `social_pattern_detection`),
  `social_pattern_detection` (Layer-5 SC-3 over the persisted `SocialGraph`; re-identifies patterns
  across runs by type+people so `has_been_surfaced` history survives instead of duplicating every
  week), `dependency_monitor` (Layer-11 SC-4, weekly: a deterministic keyword-based
  `indicator_detector` over active episodic memories — no LLM; `previous_score` isn't persisted
  across runs yet, so `trend` reads "stable" until a future task adds cross-run storage),
  `narrative_arc` (Layer-10 SC-1, weekly: rebuilds+LLM-synthesizes the current life chapter), and
  `life_calendar` (Layer-10 SC-5, daily: lazily registers relationship milestones, fires due
  entries, generates real retrospectives via SC-4 and hands them to Layer 6).
  `start_scheduler` runs them in-process via APScheduler,
  **opt-in through `config.scheduler.enabled`** (lazy-imported so the offline gate never needs it;
  no-op if disabled/absent), started/stopped in the app lifespan.
- **Sync (Layer 12, zero-knowledge)** (`api/routes/sync.py`): `POST /sync/push`, `GET /sync/pull`,
  `GET /sync/status`. The server is a **blind relay** — it stores opaque AES ciphertext produced
  on-device by `SyncCoordinator.build_delta` (`PostgresSyncStore` → `sync_delta` table) and hands
  each device the deltas from *other* devices past its cursor (the monotonic row `id`). It never
  holds the key and never decrypts; `push` is idempotent on `delta_id`.
- **Tools (Layer 8)** (`api/routes/tools.py`): `GET /tools/pending`, `POST /tools/confirm/{id}`,
  `POST /tools/deny/{id}`, `GET /tools/history`, `POST /tools/undo/{action_id}` (exposes
  `ToolManager.undo_action`, which was implemented and tested before it had an HTTP route). A single
  `ToolManager` lives on `AppState`
  (`build_tool_manager`) with the five plugins registered against **local/offline backends** (no
  third-party creds) and a durable **`PostgresActionRecorder`** (`infra/db/action_recorder.py` →
  `tool_action` JSONB). The `/chat` pipeline runs Layer 8 **before generation** via the orchestrator's
  `tool_use` hook: a detected intent short-circuits generation with a clarification question, a
  confirmation prompt, or an executed result; SOFT/HARD actions register a pending token confirmable
  on a later request through `/tools/confirm`. `ChatResponse.tool_invoked` flags a tool turn.
  Tool **routing** stays on conservative keyword rules (no chat hijacking), while a fast lightweight
  model (**gemma2:2b**, `llm.intent` role) fills the parameters each capability declares
  (`backend/layer8_tools/llm_intent.py`), so natural-language requests form real confirmations
  instead of endless clarifications; any LLM/JSON failure degrades to keyword params.
- **Voice (Layer 9)** (`api/routes/voice.py`): `POST /voice` turns text into prosody-annotated SSML
  and dispatches it to the **Kokoro** TTS backend (`build_voice_backend` on `AppState`, httpx
  transport), returning `audio/mpeg`; degrades to `503` so the client falls back to text.
- **Conversation log + continuity** (`api/routes/messages.py`, `api/routes/continuity.py`): the single
  permanent thread is persisted per turn by `make_message_writer` → **`PostgresMessageStore`**
  (`infra/db/message_store.py` → `conversation_message`), so the chat UI loads history instead of
  replaying `/chat`. `GET /messages` (newest-first, `before` cursor) + `GET /messages/search`
  (keyword+date) + `GET /memory/search` (semantic/ANN); message **annotations**
  (`POST/DELETE /messages/{id}/bookmark|milestone`, `GET /bookmarks|/milestones`); and derived
  **continuity lenses** `GET /home` (Digital Desk: greeting, current chapter, proactive, stage +
  weather), `GET /calendar` (per-day heatmap), `GET /museum` (firsts). **Echoes:** the memories Nova
  recalled each turn (Layer-2 `ScoredMemory`) are projected by `api/echoes.py` onto
  `ChatResponse.echoes` and each Nova `MessageOut.echoes`. Product/route map: `frontend/PRODUCT_SURFACE.md`.

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
`PostgresGoalStore`, `infra/db/goal_store.py`), extracting and persisting stated goals — the pipeline
appends `GoalSignalEvent`s and calls `compute_momentum` on each turn, so `Goal.momentum_score` actually
moves instead of staying pinned at its 0.0 default (previously silently zeroing `goal_store`'s ranking
and disabling the momentum-floor gate in `accountability_modifier`), and `signal_strength` from the
extraction LLM's JSON response is threaded onto the created `Goal` instead of being dropped — and appends the
turn's crisis assessment to an append-only safety log (`make_safety_writer` → `PostgresSafetyLog`,
`infra/db/safety_store.py`), and advances a self-graduating onboarding session counter
(`make_onboarding_writer` → `PostgresOnboardingStore`, `infra/db/onboarding_store.py`) — all writers
composed via `_chain_writers`. The post-turn chain also runs the **Layer-6 proactive writer**
(`make_proactive_writer` → `api/proactive_gen.py`): each active goal with an upcoming
deadline/milestone seeds/refreshes an idempotent `goal_check_in` in the `PostgresProactiveQueue` (so
`GET /proactive` accumulates real candidates; suppressed while cold-starting), and the
**relationship writer now learns communication style** (`record_turn(user_message=…)` →
`backend/layer4_persona/style_learning.py` EMA-updates verbosity/formality/question/advice
calibration, surfaced on `GET /relationship` and folded into the persona instruction by
`build_persona`). See `docs/superpowers/specs/2026-07-05-postgres-memory-store-design.md`,
`docs/superpowers/specs/2026-07-05-layer2-write-path-persistence-design.md`, and
`docs/superpowers/specs/2026-07-05-goal-persistence-design.md`.

**Layer-13 active elicitation is live:** while cold-starting, `make_cold_start_provider`
(`api/elicitation.py`) maps the message + session position to the elicitation items' natural
triggers and surfaces at most one onboarding question per session (rate-limited, distress-suppressed,
never repeated — asked targets persist in `PostgresOnboardingStore`); the orchestrator passes
`session_id` to the `cold_start` hook and `assembly.plan` weaves the question into the planner
directive. **Not yet wired:** auth/multi-user; WebSocket transport (SSE is live); Layer-13
feature-pacing (elicitation is wired, progressive feature introduction is not); persona learning
beyond the four communication-style params. Per-layer gaps surfaced during the ongoing polish
pass (narrative threads, implicit signals, etc.) are tracked in `docs/POLISH_BACKLOG.md`, not
here — check that file before starting work on any layer. See
`docs/superpowers/specs/2026-07-04-api-conversation-endpoint-design.md`
§8 and `docs/superpowers/specs/2026-07-06-chat-streaming-and-full-integration-design.md` for the
full roadmap. **Full endpoint + schema reference: `docs/API_REFERENCE.md`.**

### Infrastructure Stack

- **API**: FastAPI (`api/main.py`) — 40+ REST routes + SSE streaming (`/chat/stream`) + Kokoro voice (`/voice`); WebSocket transport is a documented follow-up. Full reference: `docs/API_REFERENCE.md`.
- **Relational DB**: PostgreSQL (runs as its own container) — the structured/relational store for per-layer state via SQLAlchemy 2.x (`infra/db/`). Vectors live in ChromaDB, so no pgvector is used. The persistent schema is managed by **Alembic** (`alembic upgrade head`; baseline `migrations/versions/0001_baseline_schema.py` runs `create_all`); `init_db`/`create_all` remains the fast path for the offline SQLite test suite and ad-hoc bootstrap.
- **On-device DB**: SQLite for user-sensitive data (UWM, audit trail, goals, personality, safety records) owned by Layer 12. SQLCipher encryption-at-rest is designed but not yet deployed — plaintext today, a genuine deployment-infra project (key management), deliberately deferred. See `docs/POLISH_BACKLOG.md`.
- **Vector store**: **ChromaDB** (runs as its own service/container; `infra/vector_store/`) — embeddings via the Ollama `nomic-embed-text` embedding function, cosine space, collections `episodic`/`semantic`/`identity`. Supersedes the earlier hnswlib design. Note: the offline unit-test suite mocks a vector store; the real store is ChromaDB. See `docs/superpowers/specs/2026-07-04-infra-runtime-substrate-design.md`.
- **LLM inference**: fully offline via Ollama, two config-driven model tiers (`config/defaults.yaml`, override with `NOVA_MAIN_MODEL`/`NOVA_MINI_MODEL` or `docker/.env`) — **main** (`qwen2.5:7b` default, 7-11B class: System 1 + System 2 generation, and — via the System 1 client — Layer 3 classification and Layer 1 narrative observation) and **mini** (`gemma2:2b` default, 1-2B class: Layer-8 tool-intent param extraction, `llm.intent`). Embeddings: `nomic-embed-text`. No cloud provider.
- **TTS**: Kokoro (custom Docker image on port 8880, OpenAI-compatible API)
- **Background Jobs**: APScheduler via `background/scheduler.py` — memory consolidation (every 2h), proactive checks (every 30min), pattern detection + social pattern detection (weekly), integrity checks (daily), longitudinal summaries (weekly), dependency monitor (weekly, Layer-11 SC-4), narrative arc synthesis (weekly, Layer-10 SC-1), life calendar (daily, Layer-10 SC-5), goal staleness sweep (weekly, Layer-7 SC-2), post-distress gap check (daily, Layer-6 SC-1). **Implemented + wired**: each job is a `run(app_state)` callable over the Postgres stores, registered in `scheduler.JOBS` (11 entries), run in-process **enabled by default via `config.scheduler.enabled: true`** (set false to opt out; APScheduler lazy-imported so the offline gate never needs it), and individually runnable via `POST /admin/jobs/{name}` (exposed on the `/admin` frontend page).

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
