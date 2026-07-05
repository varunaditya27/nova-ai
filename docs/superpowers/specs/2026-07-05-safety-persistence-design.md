# Safety-Event Persistence — Design Spec

**Date:** 2026-07-05
**Status:** Implemented
**Scope:** Persist Layer-11 crisis assessments as append-only `SafetyEvent` records, so a turn's
`CrisisSignal` survives restarts and feeds the weekly dependency check. Second slice of increment
**#2b** (per-user state); follows the goal-persistence slice.

---

## 1. Motivation

Layer 11's SC-2 (`evaluate`) runs on every turn and produces a `CrisisSignal` (tier + detail), but it
is discarded — nothing persists the safety history that SC-4 (Dependency Monitor,
`run_weekly_dependency_check`) and audit/continuity need. This slice records each meaningful crisis
assessment to Postgres, append-only.

## 2. Design decisions

| Decision | Choice |
|---|---|
| Persistence shape | JSONB `payload` (full `CrisisSignal`, via `memory_serde`) + promoted `user_id`/`tier`/`resolved` columns — mirrors the memory/goal stores. |
| Write semantics | **Append-only** (each assessment is a new row; no upsert) — a safety log, like the audit trail. |
| What to record | Only assessments with a meaningful tier (`tier != CrisisTier.NONE`); NONE turns are not logged. |
| Wiring point | **Post-turn** writer composed via `_chain_writers`, reading `ctx.crisis_assessment.signal`. |
| Read side | `recent(user_id, limit)` for the (deferred) dependency-monitor wiring; this slice logs + exposes reads, does not yet drive SC-4. |

## 3. Components

### 3.1 `SafetyEvent` ORM → JSONB (`infra/db/models/safety.py`)
Rewrite from `tier`/`detail`/`resolved` to: promoted `user_id` (mixin), `tier` (String(16), index),
`resolved` (Boolean, default False) + `payload` (`_JSONB`). No existing code writes `safety_event`.

### 3.2 `PostgresSafetyLog` (`infra/db/safety_store.py`)
Constructed `(session_factory)`:
- `record(signal: CrisisSignal) -> None`: append a `SafetyEvent` row
  (`user_id=signal.user_id`, `tier=signal.tier`, `payload=to_jsonable(signal)`).
- `recent(user_id, limit=20) -> list[CrisisSignal]`: most-recent-first, rebuilt via `from_jsonable`.

### 3.3 Post-turn safety writer (`api/state.py`)
`make_safety_writer(session_factory) -> Callable`: reads `ctx.crisis_assessment.signal`; if the signal's
tier is meaningful (`!= "none"`), sets `signal.user_id`/`session_id` from `ctx` when empty and calls
`PostgresSafetyLog(session_factory).record(signal)`. Best-effort/swallowed; composed via `_chain_writers`
alongside the memory and goal writers.

## 4. Testing (TDD)
- `test_db_models.py` — `safety_event` payload/`tier` column shape.
- `test_postgres_safety_log.py` (SQLite) — `record` appends; `recent` returns most-recent-first and is
  user-scoped; two records for the same user both persist (append-only).
- `test_state.py` (extend) — `make_safety_writer` records a TIER_2 assessment; skips a NONE assessment.
- `tests/integration_infra/test_safety_log_postgres.py` (`@pytest.mark.docker`).
- **Invariant:** bare `python3.11` green (sqlalchemy tests skip); no new deps.

## 5. Success criteria
1. A turn assessed at a real crisis tier writes a `SafetyEvent` (JSONB) that survives restart.
2. NONE-tier turns write nothing.
3. `recent(user_id)` returns the user's events, most-recent-first, cross-user isolated.
4. Offline green; docker validates live Postgres.

## 6. Non-goals
Driving SC-4 dependency monitor from the log · resolving/closing events · L4/L5/L13 slices · Chroma ANN.
