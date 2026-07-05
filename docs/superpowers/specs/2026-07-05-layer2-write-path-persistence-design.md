# Layer-2 Postgres Write Path — Design Spec

**Date:** 2026-07-05
**Status:** Implemented
**Scope:** Wire the real `backend.layer2_memory.state_updater` into `/chat`'s post-turn path so
memory **reinforcement**, **UWM version-bump**, and a tamper-evident **audit chain** all persist to
Postgres and survive restarts. Increment **#2a** of persistence-completion; builds directly on
`PostgresMemoryStore` (PR #19, `2026-07-05-postgres-memory-store-design.md`).

---

## 1. Motivation

PR #19 made episodic memories persist, but the live `/chat` writer (`make_episodic_writer`) is a
simplified stand-in: it writes one episodic row per turn and does **not** run the real State Updater.
Three things are therefore still ephemeral:

- **Reinforcement** — `state_updater` strengthens used memories by mutating `S_current` in place; with
  a Postgres store that returns fresh deserializations, the mutation is lost unless re-saved.
- **UWM version-bump** — never applied in the live path.
- **Audit trail** — the SHA-256 hash chain (`AuditTrail`) is in-memory only; every restart loses it.

This increment closes all three by running the real `state_updater` against `PostgresMemoryStore` plus
a new `PostgresAuditTrail`.

## 2. Design decisions (approved)

| Decision | Choice |
|---|---|
| Audit persistence shape | JSONB `payload` + promoted `entry_hash`/`prev_hash`/`event_type`/`user_id` columns, via `memory_serde` — mirrors `PostgresMemoryStore`. |
| Reinforcement rule (`used_memory_ids`) | **Similarity-gated**: reinforce a recalled memory only if `cosine(memory.embedding, embed(response_text)) ≥ threshold`. Realizes `state_updater`'s "actually used in the response" contract; protects competitive recall from upward drift. |
| Reinforcement write-back | One Layer-2 edit: `state_updater` re-saves each reinforced memory (`store.save_episodic(mem)`) — store-agnostic correctness. |
| Chain continuity | `PostgresAuditTrail` loads the last `entry_hash` on init so the chain continues across restarts. |
| Opaque ids | `session_id`/`memory_id` remain opaque strings; `memory_serde` is lenient (consistent with PR #19). |

## 3. Components

### 3.1 `memory_audit` ORM → JSONB payload (`infra/db/models/memory.py`)
Rewrite `MemoryAudit` from the thin `event`/`reason`/`prev_hash`/`entry_hash` columns to:
promoted indexed `user_id` (mixin), `entry_hash` (String(64), unique), `prev_hash` (String(64),
nullable), `event_type` (String(64), indexed) + `payload` (`_JSONB`) holding the full `AuditEvent`.
The thin model cannot hold the ten fields the SHA-256 chain hashes; JSONB round-trips them losslessly.
No existing code writes `memory_audit`, so this is a safe rewrite. `EXPECTED_TABLES` unchanged
(same table name).

### 3.2 `PostgresAuditTrail` (`infra/db/audit_trail.py`)
Implements Layer 2's `AuditTrail` interface (`append(event) -> AuditEvent`, `verify() -> bool`),
constructed per-user `(session_factory, user_id)`:
- **Init:** query the user's most-recent row (by `id` desc); its `entry_hash` becomes the in-memory
  chain head, else `GENESIS_HASH`.
- **`append(event)`:** set `event.prev_event_hash = head`; `event.content_hash =
  compute_event_hash(event)`; persist a `MemoryAudit` row (`payload=to_jsonable(event)`,
  `entry_hash=content_hash`, `prev_hash=prev_event_hash`, `event_type=event.event_type.value`,
  `user_id`); advance `head = content_hash`; return the event.
- **`verify()`:** reload the user's rows ordered by `id`, rebuild each `AuditEvent` from `payload`, and
  recompute the chain (`prev_event_hash` continuity + `content_hash == compute_event_hash(event)`).
  Any tampered row fails it — the tamper-evidence guarantee, now durable.

To avoid importing a private, `backend/layer2_memory/audit_trail.py` exposes its hash function as a
public `compute_event_hash` (the existing `_compute_hash` becomes a thin alias — behavior-preserving).

### 3.3 `state_updater` re-save (`backend/layer2_memory/state_updater.py`)
After `mem.S_current = ms.reinforce(mem.S_current, signal)` (and the `reinforcement_count` bump), add
`store.save_episodic(mem)` so the new strength persists. Store-agnostic; the in-memory store's
`save_episodic` is an idempotent re-put, so existing behavior is preserved. This is the single
intentional Layer-2 change, guarded by existing tests plus a new persistence test.

### 3.4 Similarity gate helper
A small pure helper (co-located with the writer) computing `used_memory_ids` from a response embedding
and the recalled `ScoredMemory` list:
`used_memory_ids(response_embedding, scored_memories, threshold) -> set` using
`backend.layer2_memory.embedding.cosine_similarity`. Default `threshold` from
`config['memory']['reinforcement_similarity_threshold']` (added to `config/defaults.yaml`, default
`0.5`).

### 3.5 `make_state_update_writer` (`api/state.py`)
Replaces `make_episodic_writer(store, embed_client, session_factory)` with
`make_state_update_writer(store, embed_client, session_factory, threshold)`. Post-turn it:
1. Upserts the `Session` turn_count (unchanged).
2. Embeds `ctx.response_text`; computes `used_memory_ids` (§3.4) over `ctx.recalled_memories`.
3. Builds a throwaway `ShortTermMemoryBuffer`, an `extractor_fn` closure yielding one `EpisodicMemory`
   from `ctx.message` + `embed([ctx.message])[0]` (same episode written today), an `emotion` from
   `ctx.emotion_intent` (neutral `EmotionVector()` fallback), and
   `audit = PostgresAuditTrail(session_factory, ctx.user_id)`.
4. Calls the **real** `state_updater(ctx.user_id, ctx.session_id or "default", stm, store, audit,
   emotion, ctx.now, extractor_fn, last_recall=ctx.recalled_memories, used_memory_ids=used)`.

Whole writer is best-effort and exception-swallowed (post-turn invariant). `build_app_state` passes
the store, embed client, session_factory, and threshold.

## 4. Data flow (post-turn)
deliver → `state_update(ctx)` → embed(response) → similarity-gated `used_memory_ids` →
`state_updater`: extract+`save_episodic` new episode (→ `MEMORY_CREATED` audit row); for each
recalled-and-used memory, `reinforce` + **`save_episodic` re-save** (→ `MEMORY_REINFORCED` audit row);
UWM version-bump if a UWM exists (→ `UWM_UPDATED` audit row) → `Session` turn_count upsert. Audit rows
are a continuing SHA-256 chain in `memory_audit`.

## 5. Error handling
- The writer swallows + logs (post-turn invariant: never affects the delivered response).
- `state_updater`'s `_safe_audit` already swallows audit-write failures, so a failed audit append never
  blocks the state update.
- `verify()` is a diagnostic, never on the hot path.

## 6. Testing (TDD)
- `test_db_models.py` — `memory_audit` payload/hash-column shape.
- `test_audit_trail_postgres.py` (SQLite) — chain build (prev/entry hashes advance); `verify()` true on
  an intact chain; tampering a persisted row's payload makes `verify()` false; **restart continuity**:
  a rebuilt `PostgresAuditTrail`'s next append has `prev_event_hash == last entry_hash`.
- `test_state_updater_persists.py` — real `state_updater` against `PostgresMemoryStore` +
  `PostgresAuditTrail`: new episode persisted; a memory in `used_memory_ids` has its `S_current`
  increased **and persisted** (visible from a rebuilt store); one not in the set is unchanged;
  `MEMORY_CREATED` + `MEMORY_REINFORCED` rows present.
- `test_reinforcement_gate.py` — the similarity helper includes reflected memories, excludes
  unreflected ones, at the threshold boundary.
- `test_state.py` (extend) — `make_state_update_writer` end-to-end over SQLite: audit rows written;
  only similarity-matched recalled memories reinforced.
- `tests/integration_infra/test_audit_trail_postgres.py` (`@pytest.mark.docker`) — audit +
  reinforcement round-trip against live Postgres.
- **Invariant:** bare `python3.11` suite green (sqlalchemy tests skip); no new hard deps.

## 7. Success criteria
1. A durable, verifiable audit chain exists in `memory_audit` and continues after a restart.
2. A response-reflected recalled memory's `S_current` increases and persists across a store rebuild; an
   unreflected recalled memory does not.
3. New episodic writes still persist (PR #19 behavior retained).
4. Offline suite green; `@pytest.mark.docker` validates the live-Postgres round-trip.

## 8. Non-goals (later increments)
Per-user Layer 4/5/7/11/13 state (#2b) · real STM-buffer plumbing (extractor uses the turn message) ·
LLM-based usage attribution · narrative-chain persistence (`detect_narrative_links`) · Chroma ANN
live-path (#3) · Alembic migrations (#4).
