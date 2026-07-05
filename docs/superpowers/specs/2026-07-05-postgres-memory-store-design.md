# PostgresMemoryStore — Layer-2 Store↔ORM Bridge — Design Spec

**Date:** 2026-07-05
**Status:** Implemented
**Scope:** Give Layer 2 a Postgres-backed memory store that is a drop-in replacement for
`InMemoryMemoryStore`, so `/chat` accumulates real, recallable episodic memories that survive a
process restart. This is sub-project **#1** of the four documented under §8.A ("Persistence
completion") in `2026-07-04-api-conversation-endpoint-design.md`.

---

## 1. Motivation

Today `build_app_state` wires `InMemoryMemoryStore()` into the pipeline, and the post-turn writer
(`make_session_writer`) persists only a placeholder `EpisodicMemory` row (the raw message as
`summary`). Nothing the arbiter recalls is read back from Postgres, and every process restart begins
with an empty memory. Nova is meant to *accumulate context across years* — persistence is the
foundational gap.

This increment closes it for the episodic/semantic/identity/UWM memory stores: a real
`PostgresMemoryStore` behind Layer 2's existing store interface, wired into both the read path
(`memory_arbiter`) and a real post-turn episodic write.

## 2. Decomposition context (why this scope)

The documented "Persistence completion" (§8.A of the API spec) is four independent subsystems. Each
gets its own spec → plan → TDD cycle. This spec is **#1 only**:

| # | Sub-project | This spec? |
|---|---|---|
| 1 | Layer-2 memory store↔ORM bridge (`PostgresMemoryStore`) | **Yes** |
| 2 | Per-user state persistence (Layer 4/5/7/11/13 → ORM) + reinforcement/UWM/audit write-back | No — follow-up |
| 3 | Chroma live-path ANN candidate selection | No — follow-up |
| 4 | Alembic migrations (replace `init_db`/`create_all`) | No — follow-up |

## 3. Design decisions (approved)

| Decision | Choice |
|---|---|
| Persistence shape | JSONB `payload` column (lossless dataclass round-trip) + a few **promoted, indexed** query columns the read path filters on. |
| SQLite/Postgres portability | `JSON().with_variant(JSONB, "postgresql")` — real JSONB in prod, TEXT-JSON on in-memory SQLite so the offline suite stays green with no Postgres dependency. |
| `user_id` identity | Treat `user_id` as an **opaque string key** end-to-end. The pipeline already uses strings (`TurnContext.user_id: str`, ORM `String(64)`); the Layer-2 dataclass `UUID` annotation is advisory and every store filter is equality-based, so no UUID coercion is introduced. |
| Write path | Wire a **real episodic write** into `/chat` (embed the turn, `save_episodic`), replacing the placeholder writer. Reinforcement / UWM version-bump / audit persistence deferred to #2. |
| Read path | Swap the store; **no arbiter changes**. Candidates scored in Python as today (Chroma ANN is #3). |

## 4. Components

### 4.1 `infra/db/memory_store.py` — `PostgresMemoryStore`
Constructed with a `session_factory`; opens a `session_scope` per operation. Implements the **exact**
interface the arbiter and write path already call, so it is a literal drop-in for
`InMemoryMemoryStore` (verified against `backend/layer2_memory/memory_store.py`):

- **Episodic:** `save_episodic(m) -> UUID`, `get_episodic(memory_id) -> EpisodicMemory | None`,
  `all_episodic(user_id) -> list`, `active_episodic(user_id) -> list` (not deleted, not archived).
- **Semantic:** `save_semantic(m) -> UUID`, `active_semantic(user_id) -> list` (not deprecated).
- **Identity (cross-user):** `save_identity(b) -> UUID`, `identity_beliefs() -> list`.
- **Recall candidates:** `candidate_memories(user_id) -> list[Memory]` = active episodic + active
  semantic.
- **UWM:** `save_uwm(uwm)`, `load_uwm(user_id) -> UserWorldModel | None`,
  `query_uwm(user_id, query_type, context="") -> dict`.

`query_uwm` loads the UWM dataclass and **delegates to the same typed-query logic** used by
`InMemoryMemoryStore.query_uwm` (extracted to a shared helper so the five query types live in one
place and both stores stay in lock-step).

Each method opens a short-lived `session_scope`, does its query/write, and returns **detached
dataclasses** (via `memory_serde`) — the ORM rows never escape the store.

### 4.2 Data model (`infra/db/models/memory.py`)
The three thin memory models are rewritten to payload-carrying shape; a `UserWorldModel` table is
added to the same module (memory-domain models stay together) and exported from
`infra/db/models/__init__.py`.

| Model | Promoted, indexed columns | Payload |
|---|---|---|
| `EpisodicMemory` | `user_id` (mixin), `memory_id` (String(36), unique), `created_at` (from the dataclass, not row-insert time), `is_deleted`, `is_archived`, `vector_id` (nullable — Chroma link for #3) | `payload` JSONB |
| `SemanticMemory` | `user_id` (mixin), `memory_id` (String(36), unique), `is_deprecated` | `payload` JSONB |
| `IdentityMemory` | `belief_id` (String(36), unique), `key` (indexed), `is_immutable` — **cross-user**, keeps `TimestampMixin` only | `payload` JSONB |
| `UserWorldModel` (new) | `user_id` (String(64), unique) | `payload` JSONB |

Notes:
- `payload = mapped_column(JSON().with_variant(JSONB, "postgresql"))`.
- `memory_id` / `belief_id` / `user_id` are the **upsert keys**: `save_*` is insert-or-replace
  (`ON CONFLICT`-style: query by key, update payload + promoted columns if present, else insert). This
  makes future in-place reinforcement re-saves idempotent.
- `created_at` is populated from the dataclass's own `created_at` so temporal recall scoring is
  identical before and after a restart. (The mixin default only applies when the dataclass omits it.)
- **Blast radius:** the current `make_session_writer` and `tests/unit/infra/test_db_models.py` /
  `tests/unit/api/test_state.py` reference the old thin columns (`summary`, `importance`). They are
  updated as part of this increment.

### 4.3 `infra/db/memory_serde.py` — serialization
`to_payload(obj) -> dict` and `from_payload(kind, dict) -> obj` for `EpisodicMemory`,
`SemanticMemory`, `IdentityMemory`, and `UserWorldModel`. Responsibilities:
- UUID ↔ str, datetime ↔ ISO-8601 string, `Enum` ↔ value, `list[UUID]` ↔ `list[str]`.
- Nested dataclasses: `EmotionVector`, `RecallEvent` list, and the UWM's nested structures
  (profile, relationship_graph, life_context, psychological_model, communication_model).
- **Primary safety property:** `from_payload(kind, to_payload(m)) == m` for representative instances
  of each type (dataclass `__eq__` on rebuilt objects). This is the fidelity guarantee for the whole
  increment and is tested hardest.

Implementation approach: a JSON-safe encoder over `dataclasses.asdict` for `to_payload`, and a typed
field-aware rebuild for `from_payload` (per-type, so UUID/datetime/nested fields are reconstructed to
their real Python types rather than left as strings).

### 4.4 Read-path wiring (`api/state.py`)
`build_app_state`: replace `InMemoryMemoryStore()` with `PostgresMemoryStore(session_factory)`. The
arbiter is unchanged — `candidate_memories(user_id)` now issues a filtered Postgres query, and scoring
runs in Python exactly as before. `build_app_state` remains fully override-injectable (tests pass a
SQLite engine).

### 4.5 Write-path wiring (`api/state.py`, `api/assembly.py`)
Replace `make_session_writer` with `make_episodic_writer(store, embedder, session_factory)`:
1. Keep the `Session` turn_count upsert (session bookkeeping — unchanged behavior).
2. Build a **real** `EpisodicMemory` dataclass from the turn:
   - `summary = message` (LLM-summarization Episodic Extractor is explicitly deferred),
   - `embedding = embedder.embed(message)` (real vector via the injected embedder),
   - `created_at = ctx.now`, `user_id = ctx.user_id`, `session_id` derived from `ctx.session_id`,
   - emotion/importance populated from classification if present on `ctx`, else defaults.
3. `store.save_episodic(episode)` → persists the JSONB row.

Still best-effort and exception-swallowed (post-turn invariant: bookkeeping never affects the already
delivered response). `build_app_state` passes the store + embedder into the writer.

## 5. Data flow (a turn, after this increment)
`POST /chat` → `run_turn` → L2 `recall` reads **candidates from Postgres** (`PostgresMemoryStore`) →
… → deliver → post-turn `make_episodic_writer`: `Session` turn_count upsert + embed(message) +
`store.save_episodic` (**JSONB row written**). Next turn / after restart: `candidate_memories` returns
the persisted memory and the arbiter can recall it.

## 6. Error handling
- **Reads:** `PostgresMemoryStore` lets exceptions propagate. `memory_arbiter` already wraps
  `candidate_memories` and `load_uwm` in the §15 fallback (`recall_degraded` / `uwm_unavailable` →
  confabulation guard), so a DB blip degrades gracefully rather than 500-ing `/chat`.
- **Writes:** the episodic writer swallows + logs (post-turn invariant).
- **Portability:** the `JSON`/`JSONB` variant keeps the SQLite offline path identical to production
  semantics for round-trips.

## 7. Testing (TDD)
- `tests/unit/infra/test_memory_serde.py` — round-trip fidelity for all four types; edge cases (empty
  embedding, populated `recall_history`, immutable identity, fully populated UWM). No third-party deps.
- `tests/unit/infra/test_postgres_memory_store.py` (`importorskip("sqlalchemy")`) — SQLite in-memory:
  save/get/all/active/candidate; `is_deleted` / `is_archived` / `is_deprecated` filtering; cross-user
  isolation; identity cross-user visibility; `memory_id` upsert (second save replaces, not
  duplicates); UWM save/load/`query_uwm` for all five query types.
- `tests/unit/infra/test_store_arbiter_integration.py` — the **real** `memory_arbiter` against
  `PostgresMemoryStore(SQLite)` + `DeterministicEmbedder`: seeded memories are recalled; empty store
  sets `cold_start` + `confabulation_guard`.
- `tests/unit/api/test_state.py` (extend) — **restart simulation**: run a turn so an episodic memory
  is written; build a *fresh* `PostgresMemoryStore` over the same engine and assert `candidate_memories`
  (and a real recall) returns it. Update the existing writer test to the new model shape.
- `tests/unit/infra/test_db_models.py` (update) — new column/payload shape for the three rewritten
  models + the new UWM model.
- `tests/integration_infra/test_memory_store_postgres.py` (`@pytest.mark.docker`) — same round-trip and
  recall against the live Postgres container (validates real JSONB).
- **Invariant:** `pytest tests/` stays green and offline on bare Python whether or not the
  `infra`/`api` extras are installed (importorskip guards); no new hard dependencies.

## 8. Success criteria
1. A `/chat` turn writes a real `EpisodicMemory` JSONB row carrying a non-empty embedding.
2. A subsequent turn — including from a `PostgresMemoryStore` rebuilt over the same database — recalls
   that memory through the real `memory_arbiter`.
3. Offline suite green on bare Python; the `@pytest.mark.docker` test validates the live Postgres JSONB
   round-trip.
4. No Layer-2 code changes required (the store is a faithful drop-in).

## 9. Non-goals (each its own later increment)
- Chroma live-path ANN candidate selection (#3) — candidates are still loaded and scored in Python.
- Per-user Layer 4/5/7/11/13 state persistence (#2).
- Reinforcement write-back, UWM version-bump persistence, and audit-trail persistence (#2). **Gotcha to
  carry forward:** `state_updater` reinforces by mutating the dataclass in place; against a store that
  returns fresh deserializations this does **not** write through, so #2 must add an explicit re-save
  (the `memory_id` upsert key is already in place to make that clean).
- Alembic migrations (#4) — schema still via `init_db`/`create_all` this increment.
- LLM-summarization Episodic Extractor (`summary` is the raw message for now).
