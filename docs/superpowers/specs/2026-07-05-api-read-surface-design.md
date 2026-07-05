# API Read Surface — Design Spec

**Date:** 2026-07-05
**Status:** Approved (design)
**Scope:** Expose the persisted domain state (goals, memory, safety, onboarding, sessions) as REST
endpoints wired end-to-end through `AppState`, so `POST /chat` writes are readable back via `GET`.
Completes the single-user backend API surface (increment **B**, read portion).

---

## 1. Motivation

`POST /chat` now persists episodic/semantic memory, goals, safety events, and onboarding progression,
but nothing exposes them — the backend can't be inspected. This increment adds the read routes the
route stubs (`api/routes/{goals,memory}.py`) document, plus safety/onboarding/sessions, each backed by
the stores shipped in PRs #19–#24. Single-user (`state.default_user_id`), no auth (consistent with the
current design).

## 2. Design decisions

| Decision | Choice |
|---|---|
| Auth | None — single-user via `state.default_user_id` (env `NOVA_USER_ID`). Multi-user/JWT is a separate subsystem. |
| Store access | Routes build the relevant Postgres store from `state.session_factory` + `state.default_user_id` (a `Depends(get_state)`). |
| Response models | Pydantic `*Out` models in `api/schemas.py`; routes map dataclasses → `*Out` defensively (`getattr`). |
| Mutations | `POST /goals` (create a goal directly) included; other mutations/deletes deferred (they need Layer 12 / lifecycle wiring). |
| Errors | Missing resource → 404; store failure → 503 (never leak internals), matching `chat`/`health`. |

## 3. Endpoints

- **Goals** (`api/routes/goals.py`): `GET /goals` (optional `?status=`; default active tiers) →
  `list[GoalOut]`; `GET /goals/{goal_id}` → `GoalOut` | 404; `POST /goals {title, description?}` →
  `GoalOut` (via `PostgresGoalStore.add_goal`).
- **Memory** (`api/routes/memory.py`): `GET /memory/audit` → `MemoryAuditOut {episodic: [...],
  semantic: [...]}` (active episodic + semantic); `GET /memory/{memory_id}` → `MemoryOut` | 404.
- **Safety** (`api/routes/safety.py`): `GET /safety/events?limit=` → `list[SafetyEventOut]`
  (`PostgresSafetyLog.recent`).
- **Onboarding** (`api/routes/onboarding.py`): `GET /onboarding` → `OnboardingOut`
  (`PostgresOnboardingStore.state`).
- **Sessions** (`api/routes/sessions.py`): `GET /sessions` → `list[SessionOut]` (Session rows).

## 4. Schemas (`api/schemas.py`)
`GoalOut {goal_id, title, status, progress_score, description}`, `GoalCreate {title, description?}`,
`MemoryOut {memory_id, summary, importance, created_at?, topic_tags}`,
`SemanticOut {memory_id, statement, confidence}`, `MemoryAuditOut {episodic, semantic}`,
`SafetyEventOut {tier, confidence, detected_at?, signal_types}`,
`OnboardingOut {cold_start_active, session_index}`, `SessionOut {session_key, turn_count}`.

## 5. Wiring
`api/main.py` includes the five new routers. `api/dependencies.py` gains small store factories
(`goal_store_for`, `memory_store_for`, etc.) or routes build stores inline from `state`.

## 6. Testing (TDD)
- Per-router unit tests (`importorskip("fastapi")`, `TestClient` + `dependency_overrides[get_state]`
  to a `SimpleNamespace` over an in-memory-SQLite `session_factory` seeded via the stores): shape +
  404 + empty cases.
- `test_app_read_e2e.py` — real `build_app_state` over SQLite with a goal-returning fake system1:
  `POST /chat "I want to run a 5k"` → `GET /goals` shows it, `GET /memory/audit` shows the episodic,
  `GET /onboarding` reflects the session. Proves the write→read loop end-to-end.
- **Invariant:** bare `python3.11` green (api tests importorskip fastapi); no new deps.

## 7. Success criteria
1. Every persisted domain (goals/memory/safety/onboarding/sessions) is readable via REST.
2. A `/chat` turn's writes are visible through the GET routes in the same app (E2E test).
3. Offline suite green.

## 8. Non-goals (separate subsystems)
Auth / multi-user (JWT, users table) · WebSocket `/chat/stream` · Layer-8 tools confirmation/execution ·
Layer-12 sync + deletion workflow · goal/memory PATCH/DELETE mutations.
