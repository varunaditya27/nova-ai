# Onboarding-State Persistence — Design Spec

**Date:** 2026-07-05
**Status:** Approved (design)
**Scope:** Persist Layer-13 cold-start progression (active flag + session count) to Postgres so
onboarding advances across restarts and self-graduates. Third slice of increment **#2b**.

---

## 1. Motivation

Onboarding (Layer 13) is inherently multi-session, but no state persists — every restart re-enters
cold start. This slice persists a minimal, self-contained onboarding record (active flag + count of
distinct sessions) that increments per new session and graduates at a threshold. The full
`ColdStartEngine` session-context wiring stays deferred (it needs a rich session context not yet
available) — this slice is the persistence substrate it will read.

## 2. Design decisions

| Decision | Choice |
|---|---|
| Persistence shape | promoted `user_id` (unique) + `cold_start_active` columns + `payload` JSONB (`session_index`, `counted_session_keys`). |
| Session counting | Self-contained: a session is counted once (tracked by `counted_session_keys` in the payload) — no coupling to the `Session`-row write ordering. |
| Graduation | When `session_index >= graduation_sessions` (config `onboarding.graduation_sessions`, default 5), set `cold_start_active = False`. |
| Wiring point | Post-turn writer composed via `_chain_writers`. |
| User scoping | Store bound to one `user_id`; all queries filter by it (per-user row, `user_id` unique). |

## 3. Components

### 3.1 `OnboardingState` ORM (`infra/db/models/onboarding.py`)
promoted `user_id` (mixin, unique via `UniqueConstraint`), `cold_start_active` (Boolean, default True) +
`payload` (`_JSONB`).

### 3.2 `PostgresOnboardingStore` (`infra/db/onboarding_store.py`)
Constructed `(session_factory, user_id, graduation_sessions=5)`:
- `state() -> dict`: current `{cold_start_active, session_index, counted_session_keys}` (defaults for a
  new user: active True, index 0, empty list).
- `record_turn(session_key) -> None`: if `session_key` not already counted, append it, `session_index += 1`,
  and set `cold_start_active = False` once `session_index >= graduation_sessions`; upsert the row.

### 3.3 Post-turn writer (`api/state.py`)
`make_onboarding_writer(session_factory, graduation_sessions) -> Callable`:
`PostgresOnboardingStore(session_factory, ctx.user_id, graduation_sessions).record_turn(ctx.session_id or "default")`.
Best-effort/swallowed; composed via `_chain_writers`. `graduation_sessions` from
`config['onboarding']['graduation_sessions']` (default 5).

## 4. Testing (TDD)
- `test_db_models.py` — `onboarding_state` payload/`cold_start_active` shape.
- `test_postgres_onboarding_store.py` (SQLite) — new user defaults to active; distinct sessions
  increment the count (same key counted once); graduation flips `cold_start_active` at the threshold;
  user-scoped.
- `test_state.py` (extend) — `make_onboarding_writer` records a session; a second session graduates at
  threshold=2.
- `tests/integration_infra/test_onboarding_store_postgres.py` (`@pytest.mark.docker`).
- **Invariant:** bare `python3.11` green; no new deps.

## 5. Success criteria
1. A user's onboarding record persists and its session count advances across restarts.
2. The same session key does not double-count; the flag graduates at the threshold.
3. Offline green; docker validates live Postgres.

## 6. Non-goals
`ColdStartEngine` session-context wiring · elicitation/feature-pacing persistence · L4 persona / L5
relationship slices · Chroma ANN.
