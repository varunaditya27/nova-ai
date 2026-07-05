# Goal Persistence — Design Spec

**Date:** 2026-07-05
**Status:** Implemented
**Scope:** Persist Layer-7 goals to Postgres and run the real `run_goal_pipeline` on the post-turn
path, so goals the user states are extracted, tracked, and survive restarts. First slice of
increment **#2b** (per-user Layer 4/5/7/11/13 state); establishes the load+save pattern the other
four layer slices reuse.

---

## 1. Motivation

Layer 7 (Goals & Accountability) is implemented and tested, but no goal a user states is persisted:
`/chat` never runs the goal pipeline, and the ORM `Goal` model is a thin stub. This slice wires the
real `backend.layer7_goals.run_goal_pipeline` into the post-turn path against a Postgres-backed
`GoalStore`, so goals accumulate across sessions — the substrate the architecture's accountability
injection and progress monitoring depend on.

## 2. Decomposition context

Increment #2b persists per-user state for five layers (L4 persona, L5 relationship, L7 goals,
L11 safety, L13 onboarding). Each needs the same **load-at-turn-start + save-post-turn** loop, so #2b
is decomposed into per-layer slices. **This spec is the L7 Goals slice** — chosen first because it is
the most self-contained (Layer 7's `run_goal_pipeline` already encapsulates the flow behind a
`GoalStore` interface), maps cleanly onto the post-turn State-Updater write path, and is architecturally
the accountability/longitudinal substrate. Remaining slices (L4/L5/L11/L13) are follow-ups.

## 3. Design decisions

| Decision | Choice |
|---|---|
| Store persistence shape | JSONB `payload` (full Layer-7 `Goal` dataclass, via `memory_serde`) + promoted indexed `user_id`/`goal_id`(unique)/`status` columns — mirrors `PostgresMemoryStore`. |
| Store implementation | `PostgresGoalStore(GoalStore)` overrides `add_goal`/`get`/`load_by_status`/`update_goal` (Postgres); **inherits `get_relevant_goals`** unchanged (it is expressed via `self.load_by_status` + pure scoring). |
| Progress-update write-back | One Layer-7 edit: add `GoalStore.update_goal(goal)` (in-memory: replace-by-id, append-if-absent) and call it in `run_goal_pipeline` after the SC-3 progress mutation — so progress persists through a Postgres store. Behavior-preserving for the in-memory store (same object identity). |
| Wiring point | **Post-turn** (write-separation invariant): a `make_goal_writer` runs `run_goal_pipeline` with `extractor_llm_fn` + `similarity_fn`, composed alongside the memory writer. |
| Read side (accountability injection into generation) | **Deferred** — a follow-up slice runs the read-only relevance/accountability part before `plan`. This slice persists + tracks; it does not yet inject goal references into responses. |
| Opaque ids | `goal_id`/`user_id` are already `str` on the Layer-7 `Goal` dataclass — no coercion; `memory_serde` lenient decoding applies. |

## 4. Components

### 4.1 `Goal` ORM → JSONB payload (`infra/db/models/goals.py`)
Rewrite from `description`/`status`/`progress` to: promoted `user_id` (mixin), `goal_id` (String(36),
unique, index), `status` (String(32), index) + `payload` (`_JSONB`). No existing code writes the `goal`
table, so this is a safe rewrite. `EXPECTED_TABLES` unchanged.

### 4.2 `GoalStore.update_goal` + engine call (`backend/layer7_goals/goal_store.py`, `engine.py`)
- Add `update_goal(self, goal: Goal) -> None` to the in-memory `GoalStore`: replace the goal with the
  same `goal_id` in `self.goals`, or append if absent.
- In `run_goal_pipeline`, immediately after `progress_monitor.update_progress_score(top, progress_signal)`
  and `top.last_mentioned_at = now`, add `goal_store.update_goal(top)`. Behavior-preserving for the
  in-memory store (the returned `top` is the same object already in `self.goals`); enables persistence
  for `PostgresGoalStore`. Guarded by existing Layer-7 tests + a new persistence test.

### 4.3 `PostgresGoalStore` (`infra/db/goal_store.py`)
`PostgresGoalStore(GoalStore)` constructed `(session_factory, user_id)`:
- `add_goal(goal)`: upsert by `goal_id` (insert or replace payload + promoted columns).
- `update_goal(goal)`: same upsert (idempotent).
- `get(goal_id) -> Goal | None`: query by `goal_id`, rebuild via `from_jsonable`.
- `load_by_status(statuses) -> list[Goal]`: `WHERE user_id = self._user_id AND status IN statuses`,
  rebuild each.
- `get_relevant_goals(...)`: **inherited** — uses the overridden `load_by_status`.

### 4.4 Post-turn goal writer (`api/state.py`)
`make_goal_writer(session_factory, system1_client, embed_client) -> Callable`:
- Builds `extractor_llm_fn` = a JSON-returning wrapper over `system1_client.complete` (returns the
  model's JSON string; `extract_goal` parses it, with a safe fallback on non-JSON).
- Builds `similarity_fn(a, b)` = `cosine_similarity(embed([a])[0], embed([b])[0])`.
- Post-turn: `run_goal_pipeline(ctx.message, goal_store=PostgresGoalStore(session_factory, ctx.user_id),
  message_id=ctx.session_id or "", extractor_llm_fn=..., similarity_fn=..., now=ctx.now)`.
- Best-effort and exception-swallowed (post-turn invariant).

`build_app_state` composes the memory writer and the goal writer into one `session_writer` via a small
`_chain_writers(*writers)` helper (each called in its own try/except so one failing never blocks the
other or the turn).

## 5. Data flow (post-turn)
deliver → `state_update(ctx)` → [memory `state_updater` writer] **+** [goal writer:
`run_goal_pipeline` → extract goal from the message (dedup against active goals) → `add_goal`; classify
progress on the top relevant goal → `update_goal`] → goals persisted in the `goal` table (JSONB),
recallable next session.

## 6. Error handling
- Each composed writer runs in its own `try/except` (swallow + log); a goal-writer failure never affects
  the memory writer or the delivered response.
- `run_goal_pipeline` already wraps each sub-step in `_safe(...)` (failures degrade to empty/no-op).

## 7. Testing (TDD)
- `test_db_models.py` — `goal` payload/`goal_id`/`status` column shape.
- `test_postgres_goal_store.py` (SQLite) — `add_goal`/`get`/`load_by_status` (status filter);
  `goal_id` upsert (no duplicate); cross-user isolation; `get_relevant_goals` (inherited) ranks a
  status/recency-matched goal; `update_goal` replaces.
- `test_goal_pipeline_persists.py` — real `run_goal_pipeline` against `PostgresGoalStore` with a fake
  `extractor_llm_fn` returning a `goal_detected` payload: a new goal is persisted (visible from a
  rebuilt store); a progress mention on an existing goal updates its momentum **and persists**.
- Layer-7 regression: existing `GoalStore`/`run_goal_pipeline` tests stay green after `update_goal`.
- `test_state.py` (extend) — `make_goal_writer` end-to-end over SQLite persists an extracted goal;
  `_chain_writers` runs both writers.
- `tests/integration_infra/test_goal_store_postgres.py` (`@pytest.mark.docker`) — goal round-trip +
  pipeline against live Postgres.
- **Invariant:** bare `python3.11` suite green (sqlalchemy tests skip); no new hard deps.

## 8. Success criteria
1. A goal stated in a `/chat` turn is extracted post-turn and persisted to the `goal` table (JSONB).
2. A later turn — including from a rebuilt `PostgresGoalStore` — loads it via `load_by_status`; a
   progress mention updates and persists its momentum.
3. Existing Layer-7 tests still pass (the `update_goal` addition is behavior-preserving).
4. Offline suite green; `@pytest.mark.docker` validates the live-Postgres round-trip.

## 9. Non-goals (follow-up slices)
Accountability-injection of goal references into generation (read side) · goal decomposition + Layer-6
handoff wiring · L4 persona / L5 relationship / L11 safety / L13 onboarding persistence (other #2b
slices) · Chroma ANN (#3, deferred as YAGNI).
