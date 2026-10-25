# Nova AI — Master Architecture & Single Source of Truth

> **Status:** All 13 cognitive layers implemented, tested, documented, and integrated through a
> live conversation orchestrator. **1641 tests passing** (run with `.venv/bin/pytest`).
> **130 layer modules (~19.6k LOC) + 6 pipeline modules**, pure
> Python standard library, dependency-injected throughout.
>
> **Scope of this document.** This is the authoritative, top-level map of the entire system: what
> Nova is, how a single conversation turn flows through all 13 layers, what each layer owns, the
> cross-cutting invariants that hold system-wide, the data/storage/infra model, and how to build,
> run, and verify everything. Per-layer deep specs live in `docs/layer-N-architecture.md` (each
> ends with an "as-built" section reconciling spec ↔ code). When this document and a layer doc
> agree, treat this as the index and the layer doc as the detail. When code and any doc disagree,
> **the code is the source of truth** — every layer config and doc is reconciled against it.

---

## Table of Contents

1. [What Nova Is](#1-what-nova-is)
2. [System at a Glance](#2-system-at-a-glance)
3. [The Conversation Turn Lifecycle](#3-the-conversation-turn-lifecycle)
4. [Dual-Pipeline Routing (System 1 / System 2)](#4-dual-pipeline-routing-system-1--system-2)
5. [The 13 Layers in Detail](#5-the-13-layers-in-detail)
6. [System-Wide Invariants](#6-system-wide-invariants)
7. [Data & Storage Architecture](#7-data--storage-architecture)
8. [Infrastructure & Models](#8-infrastructure--models)
9. [Engineering Conventions](#9-engineering-conventions)
10. [Testing & Verification](#10-testing--verification)
11. [Build, Run & Operate](#11-build-run--operate)
12. [Repository Map](#12-repository-map)
13. [Delivery Provenance](#13-delivery-provenance)

---

## 1. What Nova Is

Nova AI is a **13-layer cognitive architecture for long-term human–AI companionship**. It is not
a chatbot. It is a system designed to accumulate context, continuity, emotional understanding, and
relational depth across **years** of interaction. Every architectural decision optimizes for one
thing: *being worth returning to over a long arc of someone's life.*

Three commitments shape the whole system:

- **Continuity over cleverness.** A single good answer is cheap. Nova invests in remembering,
  consolidating, and re-surfacing what matters so that the *relationship* compounds.
- **Emotional fidelity is first-class.** Emotion is not a sentiment label bolted on at the end —
  it shapes memory recall (mood-congruent recall), generation (a dedicated Emotion Refiner),
  pacing, and safety.
- **Safety and privacy are structural, not features.** Crisis handling can never be gated or
  delayed; the most sensitive user model never leaves the device; deletion is genuinely surgical;
  the audit trail is tamper-evident.

---

## 2. System at a Glance

```
                          ┌──────────────────────────────────────────────┐
   user turn ───────────► │       Conversation Orchestrator (pipeline)     │ ──► delivered reply
                          │   pure sequencing; enforces the invariants     │
                          └───────────────────────┬──────────────────────┘
                                                  │
   ┌───────────── parallel, never blocked ───────┴───────────────────────────────────┐
   │ L11 Safety (SC-2 crisis detection)                                                │
   └───────────────────────────────────────────────────────────────────────────────┘
                                                  │
   L1 Input ─► L2 Memory ─► L13 Cold-Start overlay ─► L3 Reasoning ─► route ─┬─ System 1 (fast)
                                                                              └─ System 2 (full)
                                                  │
        L4 Persona/Generation (Agent 4a + 4b) ─► L5/L7/L8 enrichment ─► L11 SC-1 guardrails
                                                  │
                          L9 Output delivery ─► reply ─► (post-turn) State Update ─► L2/L10/L12 writes
```

| # | Layer | Package | Modules | Role (one line) |
|---|---|---|---:|---|
| 1 | Input Perception | `backend/layer1_input/` | 9 | Temporal context, implicit behavioral signals, multimodal + voice prosody normalization |
| 2 | Memory | `backend/layer2_memory/` | 16 | STM + Episodic/Semantic/Identity + UWM; competitive recall, forgetting, audit |
| 3 | Reasoning | `backend/layer3_reasoning/` | 9 | Emotion + intent (shared call), background state, mismatch, empathy, mode resolution |
| 4 | Persona & Generation | `backend/layer4_persona/` | 9 | Persona/relationship state, tone, drift; Agent 4a Planner + Agent 4b Refiner |
| 5 | Relationship Intelligence | `backend/layer5_relationship/` | 8 | Social graph, interpersonal events, pattern recognition, coaching injection |
| 6 | Proactivity | `backend/layer6_proactivity/` | 9 | Proactive queue, timing/delivery gates, message generation, response tracking |
| 7 | Goals & Accountability | `backend/layer7_goals/` | 8 | Goal extraction, lifecycle, progress, accountability, decomposition → L6 |
| 8 | Tools & Actions | `backend/layer8_tools/` | 13 | Tool manager, confirmation gate (AUTO/SOFT/HARD), param resolver, plugins |
| 9 | Output Delivery | `backend/layer9_output/` | 14 | Format adaptation, micro-interactions, voice (Kokoro/SSML), streaming |
| 10 | Longitudinal | `backend/layer10_longitudinal/` | 9 | Life narrative, weekly summaries, progress/pattern, retrospective, life calendar |
| 11 | Safety & Crisis | `backend/layer11_safety/` | 9 | Ethical guardrails (SC-1), crisis detection (SC-2), escalation (SC-3), dependency (SC-4) |
| 12 | Privacy & Data | `backend/layer12_privacy/` | 9 | On-device encryption, integrity, selective deletion, audit, zero-knowledge sync |
| 13 | Onboarding / Cold Start | `backend/layer13_onboarding/` | 8 | Progressive elicitation, cold-start defaults, feature pacing, graduation |
| — | Pipeline | `backend/pipeline/` | 6 | Pure orchestration: sequences all layers + enforces invariants |

The pipeline is **pure orchestration with zero business logic** — every layer step is injected as
a callable, so a refactor inside a layer never touches pipeline code.

---

## 3. The Conversation Turn Lifecycle

The entry point is `backend/pipeline/conversation_orchestrator.py` →
`ConversationOrchestrator.run_turn(user_id, message, now, session_id)`. It threads a `TurnContext`
through the layers and returns an `OrchestratedOutput`. The exact sequence (and the invariants it
guarantees) is:

1. **Layer 11 SC-2 — Crisis detection runs first and is never blocked.** The safety scan executes
   before anything else and is wrapped so that *even if a later layer raises*, the safety result is
   already captured. Safety is conceptually parallel to the main pipeline; it is never gated by
   cold start, routing, or load.
2. **Layer 1 — Input perception.** Builds the input-perception packet: circadian band, session-gap
   context, implicit behavioral signals (latency, deletions, message length), multimodal/voice
   normalization. Raw ISO timestamps are converted to *fuzzy temporal labels* here.
3. **Layer 2 — Memory recall (read-only during inference).** Competitive recall returns at most 3
   memories. If recall is empty, the orchestrator sets the **confabulation guard** so downstream
   generation is told not to invent memories.
4. **Layer 13 — Cold-start overlay (applied after Layer 2).** If the user is still in cold start,
   the overlay constrains the turn: proactivity is `observe_only`, personality drift is gated to
   30%, and at most one naturally-triggered elicitation question may surface.
5. **Layer 3 — Reasoning.** Emotion + intent classification (a single shared fast-model call),
   stated-vs-felt mismatch, empathy hypothesis, and deterministic conversation-mode resolution.
6. **Crisis veto (OR semantics).** If SC-2 detected a crisis **or** Layer 3 raised the crisis
   flag, Layer 11 SC-3 escalation **replaces the normal response entirely** and System 1/2
   generation is skipped. Crisis resources always come from a registry, never the LLM.
7. **Generation (only when not in crisis).** The orchestrator routes to **System 1** or
   **System 2** (see §4). System 1 runs persona + Agent 4a only; System 2 adds Agent 4b.
8. **Layer 11 SC-1 — Post-generation ethical guardrails.** Runs on the generated response before
   delivery; may rewrite it and record flags.
9. **Layer 9 — Output delivery always runs.** Crisis responses are delivered as pure prose with
   micro-interactions suppressed (`crisis_mode_active=True`).
10. **Post-turn state update (final, non-blocking).** After the reply is delivered, the write path
    runs: Layer 2 episodic write + reinforcement + consolidation trigger, Layer 4 drift, Layer 5
    relationship updates, Layer 7 goal progress, Layer 10 longitudinal data, Layer 12 audit. A
    failing writer is logged and skipped — post-turn bookkeeping can never affect the delivered
    response.

**Degraded mode.** If the main path raises after the safety scan, the orchestrator returns a safe
fallback response, still delivers via Layer 9, and marks the output `degraded=True` — the safety
assessment is preserved regardless.

---

## 4. Dual-Pipeline Routing (System 1 / System 2)

After Layer 3 classifies the message, `route_system()` selects a path:

| | **System 1** (`system1_pipeline.py`) | **System 2** (`system2_pipeline.py`) |
|---|---|---|
| Trigger | casual / simple turns | mode ∈ {crisis, emotional_support, goal_planning, life_review, social_coaching} **or** complexity = complex |
| Latency target | < 2 s | < 30 s |
| Production model | Ollama, "main" tier (`NOVA_MAIN_MODEL`, default qwen2.5:7b) | same "main" tier model — depth differs by pipeline steps, not model size |
| Generation | Persona + **Agent 4a** only | Persona + **Agent 4a + Agent 4b** |
| Emotion Refiner (4b) | **skipped** | **runs** |

Independent of routing, **Layer 3's emotion+intent classifier always runs on every message**,
shared across the emotion and intent outputs in a single call (<150 ms target). The architecture
target is a dedicated fast small model (Phi-3 Mini / Gemma 2B); the wired implementation reuses
the System 1 client instead — see `CLAUDE.md`.

---

## 5. The 13 Layers in Detail

For each layer: package, primary entry point (the symbol the pipeline wires and the consistency
guard asserts), key modules, and the invariants/constants that matter most. Full specifications
are in the corresponding `docs/layer-N-architecture.md`.

### Layer 1 — Input Perception · `process_input_event`
Modules: `service`, `assembler`, `temporal_resolver`, `implicit_signals`, `multimodal_normalizer`,
`prosody_extractor`, `thread_tracker`, `schemas`.
- Produces the `InputPerceptionPacket`: circadian band, session-gap, implicit signals, modality
  context, narrative thread, temporal profile.
- **Fuzzy temporal labels only** — `fuzzy_label_for_timestamp` converts every timestamp to
  human-relative language; the LLM never sees raw ISO time.
- Heavy backends (normalizer, prosody) are optional; absent → graceful degradation.

### Layer 2 — Memory · `memory_arbiter`
Modules: `arbiter`, `stm`, `memory_store`, `semantic_memory`, `identity`, `recall_scorer`,
`competitive_recall`, `context_gate`, `forgetting_engine`, `memory_strength`, `embedding`,
`state_updater`, `audit_trail`, `memory_types`, `schemas`.
- **Stores:** STM (40-turn / 12k-char rolling, never persisted), Episodic (ChromaDB collection,
  cosine, embeddings via Ollama `nomic-embed-text`), Semantic (distilled, confidence-weighted),
  Identity (self-model; some `is_immutable`), and the **User World Model** (on-device only, never
  cloud-synced — the most sensitive structure in the system).
- **Competitive recall:** `RecallScore = α·Semantic + β·Emotional + γ·Temporal + δ·Importance`,
  defaults α=0.40, β=0.30, γ=0.20, δ=0.10; softmax temperature τ≈0.7; **max 3 memories** per call.
  β implements **mood-congruent recall** (a design decision, not a filter).
- **Forgetting & Consolidation Engine (FCE):** triggers on ≥50 new episodes / ≥25 sessions / 14
  days; runs decay sweep → agglomerative clustering (cosine 0.85, complete-linkage) → semantic
  extraction. Deletions are logical (`is_deleted`/`is_archived`); lineage retained.
- **Write separation:** all writes go through the State Updater *after* the turn; Layer 2 is
  read-only during inference. The **audit trail** is an append-only SHA-256 hash chain.

### Layer 3 — Reasoning · `build_emotion_intent_packet`
Modules: `emotion_classifier`, `intent_classifier`, `background_state`, `mismatch_detector`,
`empathy_hypothesis`, `mode_resolver`, `packet_builder`, `schemas`.
- Emotion + intent share **one** fast-model call (<150 ms). Resolves one of 8 conversation modes
  (`crisis`, `emotional_support`, `celebration`, `technical_discussion`, `goal_planning`,
  `social_coaching`, `life_review`, `casual`).
- When `crisis_flag` confidence > 0.65, emits a `CrisisAlert` to **Layer 11** immediately —
  without waiting for the full packet.
- **No raw scores to the LLM** — valence/arousal/recall floats become plain-language directives.

### Layer 4 — Persona & Two-Stage Generation · `generate_semantic_draft`
Modules: `persona_resolver`, `relationship_manager`, `tone_calibrator`, `drift_detector`,
`semantic_planner` (Agent 4a), `emotion_refiner` (Agent 4b), `packet_builder`, `schemas`.
- **Agent 4a (Semantic Planner):** factually complete content; adds *no* emotional language;
  constrained by an advice gate (`open`/`gated`/`closed`) from Layer 3.
- **Agent 4b (Emotion Refiner):** adjusts tone/warmth/validation without changing facts; skipped
  when all 5 neutral conditions hold; post-refinement factual preservation is checked via embedding
  cosine similarity on key claims.

### Layer 5 — Relationship Intelligence · `build_social_intelligence_packet`
Modules: `social_graph`, `event_tracker`, `pattern_recognizer`, `coaching_detector`,
`coaching_modifier`, `packet_builder`, `schemas`.
- Tracks the user's social graph and interpersonal events, recognizes social patterns, and injects
  *coaching opportunities* (framed as observation, never verdict).

### Layer 6 — Proactivity · `run_proactive_cycle`
Modules: `engine`, `queue_manager`, `initiative_classifier`, `timing_gate`, `message_generator`,
`response_tracker`, `intake`, `schemas`.
- Background outreach independent of user turns (scheduler ~30 min). Timing/delivery gates (DND,
  frequency) precede generation; the response tracker monitors engagement. Suppressed entirely
  during cold start.

### Layer 7 — Goals & Accountability · `run_goal_pipeline`
Modules: `engine`, `goal_extractor`, `goal_store`, `progress_monitor`, `accountability_modifier`,
`goal_decomposer`, `schemas`.
- Extracts goals from natural language, manages lifecycle/progress, injects accountability, and
  decomposes goals, handing milestones to Layer 6's proactive intake.

### Layer 8 — Tools & Actions · `ToolManager`
Modules: `tool_manager`, `confirmation_gate`, `parameter_resolver`, `action_recorder`, `schemas`,
`plugins/{base,calendar,email,notes,reminders,web_search}`.
- Flow: intent → resolve → confirm → execute → record. **Confirmation gate** tiers AUTO/SOFT/HARD;
  plugin `default_tier` is the authoritative baseline and intrinsic risk floors only *raise* it.
- **Object-capability hardening:** confirmation is bound to a SHA-256 fingerprint of
  `(tool, operation, params, user_id)`, single-use, ownership-checked; execution is fail-closed;
  the action recorder is append-only. **Crisis/safety is *not* here — it is Layer 11.**

### Layer 9 — Output Delivery · `deliver`
Modules: `interaction_orchestrator`, `format_adapter`, `length_calibrator`, `user_format_profile`,
`thinking_pause`, `self_edit_simulator`, `stream_typing_overlay`, `micro_interaction_engine`,
`voice_synthesizer`, `tts_backends/{base,kokoro}`, `schemas`.
- **Every response passes through Layer 9.** Format adaptation, micro-interactions (typing
  simulation, thinking pauses, self-editing), and voice synthesis (Kokoro TTS via SSML).
- `deliver(crisis_mode_active=True)` forces pure prose and suppresses all micro-interactions.

### Layer 10 — Longitudinal · `assemble_context_packet`
Modules: `engine`, `life_narrative_engine`, `narrative_arc`, `weekly_summary`, `progress_tracker`,
`retrospective`, `life_calendar`, `schemas`.
- Life Narrative Engine, Weekly Summary, Progress & Pattern tracker (patterns require ≥3
  occurrences **and** a confidence floor), Retrospective (surfacing windows), and Life Calendar.
- **Grounded fallbacks:** with no LLM available, summaries are factual-only — never invented
  interpretation.

### Layer 11 — Safety & Crisis · `SafetyAgent`
Modules: `safety_agent`, `ethical_guardrails` (SC-1), `crisis_classifier` (SC-2),
`escalation_engine` (SC-3), `dependency_monitor` (SC-4), `safe_mode_enforcer`, `safety_record`,
`schemas`.
- **SC-2** crisis detection runs in parallel with every message; **SC-1** ethical guardrails run
  post-generation on every response; **SC-4** dependency monitor runs weekly; **SC-3** escalation
  has **veto authority** — it discards and replaces the normal response when crisis is confirmed.
- **Asymmetric thresholds:** TIER_1 0.60 (hair-trigger), TIER_2 0.70, TIER_3 0.80 (conservative).
  Crisis resources always come from the registry (anti-hallucination). `safety_record` is a
  SHA-256 hash chain (`verify_chain`).

### Layer 12 — Privacy & Data · `PrivacyAgent`
Modules: `privacy_agent`, `encryption_manager` (SC-1), `integrity_verifier` (SC-1),
`selective_deletion` (SC-2), `memory_audit` (SC-3), `correction_interface` (SC-3),
`sync_coordinator` (SC-4), `schemas`.
- **On-device encryption** (production: AES-256-GCM via SQLCipher; stdlib runtime: a real AEAD
  construction — PBKDF2-HMAC-SHA256 → HKDF → SHA-256 CTR → HMAC encrypt-then-MAC — behind the same
  key hierarchy). **Merkle** integrity (order-independent leaves; tamper detection).
- **Selective deletion** (6 types) with dry-run *cascade* (semantic facts, longitudinal refs,
  personality shifts), secure-zero before removal, and a signed deletion certificate.
- **Zero-knowledge sync:** deltas are encrypted on-device; the server stores opaque ciphertext it
  cannot read. Crisis-session-logging consent is non-revocable.

### Layer 13 — Onboarding / Cold Start · `ColdStartEngine`
Modules: `cold_start_engine`, `passive_elicitation`, `active_elicitation_queue`,
`context_constructor`, `graduation_evaluator`, `feature_pacing`, `schemas`.
- A **temporary overlay** active from a new user's first message until graduation, then it
  self-terminates. Three principles enforced in code: **earn before asking** (a natural trigger +
  ≤1 elicitation/session for the first 14 sessions), **infer before asking** (8 passive extractors,
  no LLM), **delay features, not presence** (11-feature pacing registry).
- **Graduation:** 7 required criteria; handoff is *silent* (no user-visible change). **Safety is
  never gated** — `crisis_resource_awareness` is active from message 0 with zero prerequisites.

---

## 6. System-Wide Invariants

These hold across the entire system and are enforced in code (most are asserted by tests):

1. **Layer 9 always runs.** Every response — System 1, System 2, crisis, or degraded — is
   delivered through Layer 9.
2. **Safety is never gated or blocked.** Layer 11 SC-2 runs first and survives downstream
   failures; no cold-start exemption or routing decision can suppress it.
3. **Crisis veto.** Confirmed crisis (SC-2 OR Layer 3 flag) replaces the normal response via SC-3;
   normal generation is skipped; resources come from a registry, never the LLM.
4. **Memory writes are non-destructive & post-turn.** Layer 2 is read-only during inference; all
   writes happen in the State Updater after the turn; deletions are logical with retained lineage.
5. **Fuzzy temporal labels only.** The LLM never sees raw ISO timestamps (Layer 1 enforces this;
   Layer 4 prompt construction relies on it).
6. **No raw scores to the LLM.** Valence/arousal, recall scores, crisis confidence, and BES label
   scores become plain-language directives in Layer 3.
7. **Confabulation guard.** Empty recall ⇒ downstream prompt is explicitly told not to invent or
   imply specific memories.
8. **UWM stays on-device.** The User World Model is never cloud-synced.
9. **Pure orchestration.** The pipeline carries no business logic; layers are injected; the
   `PipelineSteps` contract is the single integration seam.

---

## 7. Data & Storage Architecture

| Concern | Store | Notes |
|---|---|---|
| Relational data | PostgreSQL (`infra/db/`, SQLAlchemy 2.x) | per-layer structured state; vectors live in Chroma, so no pgvector |
| On-device sensitive | SQLite + SQLCipher | UWM, audit trail, goals, personality, safety records — encrypted at rest (Layer 12) |
| Vector store | **ChromaDB** (service/container; `infra/vector_store/`) | collections `episodic`/`semantic`/`identity`; cosine; embeddings via Ollama `nomic-embed-text`. Supersedes the earlier hnswlib design. |
| Session cache | `infra/session_cache.py` | ephemeral per-turn buffer; distinct from Layer 2 STM |

**Tamper-evidence appears twice, by design:** Layer 2's audit trail and Layer 11's safety record
are independent SHA-256 hash chains; Layer 12 adds a Merkle root over the encrypted store.

> Implementation note: the committed code is pure-stdlib and dependency-injected so the full suite
> runs offline with no databases or model servers. Production swaps concrete backends (Postgres,
> SQLCipher, ChromaDB, Ollama, Kokoro) in behind the same interfaces/key hierarchy. The
> runtime substrate that provides those backends lives in `infra/` (config loader + role-based LLM
> factory, ChromaDB vector store, Postgres/SQLAlchemy models) and is dockerised under `docker/`
> — see `docs/superpowers/specs/2026-07-04-infra-runtime-substrate-design.md`.

---

## 8. Infrastructure & Models

| Component | Production target |
|---|---|
| API | FastAPI (`api/main.py`) — **live: 40+ REST routes across all 13 layers + SSE streaming (`/chat/stream`) + Kokoro voice (`/voice`)**; sync `/chat` bridges to the async layers via a threadpool. WebSocket transport is a follow-up. **Full endpoint + schema reference: [`API_REFERENCE.md`](API_REFERENCE.md).** |
| Relational store | PostgreSQL 16 + SQLAlchemy 2.x (`infra/db/`) |
| Vector store | ChromaDB service (`infra/vector_store/`); Ollama `nomic-embed-text` embeddings |
| LLM inference | Fully offline via Ollama, two config-driven tiers — **main** (`NOVA_MAIN_MODEL`, default qwen2.5:7b: System 1 + System 2 generation) and **mini** (`NOVA_MINI_MODEL`, default gemma2:2b: Layer-8 tool-intent params); embeddings via `nomic-embed-text`. No cloud provider. |
| LLM client layer | `infra/llm/` — official `ollama` SDK behind one `LLMClient` ABC, config-driven factory |
| Layer 3 classifier | Phi-3 Mini / Gemma 2B target (aspirational); wired implementation reuses the System 1 client |
| Agent 4a / 4b targets | Phi-3 Medium 14B / Gemma 2 9B; Llama 3.1 8B / Gemma 2 9B Instruct (aspirational) |
| TTS | Kokoro (Docker, port 8880, OpenAI-compatible) |
| Background jobs | APScheduler (`background/scheduler.py`) — consolidation 2h, proactive 30m, patterns weekly, integrity daily, longitudinal Sunday |

Docker services (`docker/docker-compose.yml`): `postgres` :5432, `chroma` :8001→8000, `ollama`
:11434, `kokoro` :8880, and `backend` :8000 (profile `app`) on `nova-network`. All published ports
bind to `127.0.0.1`; backend runs non-root and waits for postgres/chroma/ollama healthy. The `infra`
extra in `pyproject.toml` carries the third-party deps; the base install stays pure-stdlib so the
offline suite is unaffected.

Config: `config/defaults.yaml` loads first, then per-layer `config/layerN.yaml` overrides. Each
layer config is namespaced under `layerN:` and mirrors that layer's module constants (the code is
authoritative; YAML enables retuning without code changes). The consistency guard asserts all 13
configs parse and are correctly namespaced.

---

## 9. Engineering Conventions

- **Language/runtime:** Python 3.11. The **13 cognitive layers + pipeline** are standard library only
  (dataclasses + str-`Enum`; `hashlib`/`hmac`/`secrets` for crypto) — no pydantic/numpy/sqlalchemy/
  cryptography. The **`infra/` substrate** is the sole home of third-party deps (`ollama`,
  `chromadb`, `sqlalchemy`, `psycopg`), isolated behind the `pyproject.toml` `infra` extra so the
  layer suite stays install-free and offline.
- **Dependency injection everywhere:** LLMs, stores, embedders, signers, HTTP, RNG, and clocks are
  injected callables/duck-typed objects → the system is deterministic and runs offline.
- **TDD throughout:** every layer (and the orchestrator) was built red→green per sub-component.
- **Single source of truth per layer:** code ↔ `config/layerN.yaml` ↔ `docs/layer-N-architecture.md`
  are reconciled; each layer doc has an as-built section.

---

## 10. Testing & Verification

```bash
# Everything (offline, no services needed)
/usr/bin/python3.11 -m pytest tests/ -q          # 1120 passed

# Unit only (per-component behaviour)
/usr/bin/python3.11 -m pytest tests/unit/ -q     # 1057

# Integration only (cross-layer + orchestration + consistency guards)
/usr/bin/python3.11 -m pytest tests/integration/ -q   # 63
```

**Test inventory (1120 total):**
- **1057 unit tests** across 111 files — one or more per sub-component of every layer.
- **Integration tests** (`tests/integration/`):
  - `test_full_turn_system1.py` — casual turn → System 1, 4b skipped, layer order, confabulation guard.
  - `test_full_turn_system2.py` — emotional/complex turn → System 2, 4a + 4b run.
  - `test_safety_override.py` — crisis veto, OR-semantics, safety-never-blocked, post-gen guardrail rewrite.
  - `test_cold_start_graduation.py` — cold-start overlay wiring, incl. the **real** `ColdStartEngine`.
  - `test_memory_consolidation.py` — **real** Layer 2 FCE (decay → cluster → semantic extraction).
  - `test_sync_multidevice.py` — **real** Layer 12 zero-knowledge sync + Merkle integrity.
  - `test_layer_consistency.py` — 42 parametrized guards: every layer imports, exposes its entry
    point, has a parseable namespaced config; pipeline/API import; `PipelineSteps` exposes every hook.

The consistency guard is the standing defense against integration drift: rename an export, drop a
module, or break a config namespace and exactly one guard fails with a precise message.

---

## 11. Build, Run & Operate

```bash
docker compose up -d                    # Ollama, Kokoro, backing services
uvicorn api.main:app --reload           # dev API server
pytest                                  # full suite
python scripts/seed_db.py               # sample data
python scripts/eval_recall.py           # memory recall evaluation
python scripts/export_audit.py          # export audit trail
python scripts/calibrate_weights.py     # recall-weight calibration
```

---

## 12. Repository Map

```
backend/
  layer1_input/ … layer13_onboarding/   # the 13 cognitive layers (130 modules)
  pipeline/                             # conversation_orchestrator, system1/2, state_updater, proactive
api/                                    # FastAPI app, routes, middleware
config/                                 # defaults.yaml + layer1..13.yaml
docs/
  NOVA_AI_MASTER_ARCHITECTURE.md        # ← this file (single source of truth)
  layer-1-architecture.md … layer-13-architecture.md   # per-layer specs (+ as-built sections)
tests/
  unit/                                 # 1057 tests, 111 files
  integration/                          # full-turn, safety, cold-start, consolidation, sync, consistency
scripts/                                # seed, eval, audit export, calibration
background/                             # APScheduler jobs
infra/                                  # session cache, client adapters
```

---

## 13. Delivery Provenance

| Layers | PRs | Highlights |
|---|---|---|
| 1–2 | #1 | Input perception + memory core (244 tests); arch docs reconciled to impl-ready SoT |
| 3 | #3 | Reasoning: shared emotion+intent call, modes, empathy hypothesis |
| 4–7 | #4–#7 | Persona/two-stage generation, relationship intel, proactivity, goals |
| 8 (+ hardening) | #8, #9 | Tools & Actions + object-capability hardening; Layer 8/11 mismatch resolved (L8 = tools, L11 = crisis) |
| 9 | #10 | Output delivery, micro-interactions, voice/SSML |
| 10 | #11 | Longitudinal: narrative, weekly summary, progress, retrospective, life calendar |
| 11 | #12 | Safety & crisis: guardrails, 3-tier detection, escalation veto, dependency monitor |
| 12 | #13 | Privacy: stdlib AEAD, Merkle integrity, surgical deletion, zero-knowledge sync |
| 13 | #14 | Onboarding / Cold Start: progressive elicitation, feature pacing, silent graduation |
| Integration | (this work) | Live conversation orchestrator wiring all 13 layers; full-turn/safety/cold-start/consolidation/sync integration tests; cross-layer consistency guards |

**Current state:** all 13 layers implemented, tested, documented; pipeline wired and verified;
**1120 tests green**; `main` is the single source of truth.

---

*This document is the canonical top-level reference for Nova AI. Keep it in sync with the code: if
you add a layer module, change an entry point, or alter an invariant, update §5/§6 here and the
relevant `docs/layer-N-architecture.md` as-built section in the same change.*
