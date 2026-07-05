# Goal Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Persist Layer-7 goals to Postgres and run the real `run_goal_pipeline` post-turn, so stated goals are extracted, tracked, and survive restarts.

**Architecture:** `PostgresGoalStore(GoalStore)` overrides the persistence methods (JSONB payload) and inherits `get_relevant_goals`; a post-turn `make_goal_writer` runs `run_goal_pipeline` against it, composed alongside the memory writer.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x (JSONB), pytest.

## Global Constraints

- Run sqlalchemy/pydantic tests with `.venv/bin/python -m pytest`; each starts `pytest.importorskip("sqlalchemy")`.
- **Offline invariant:** `/usr/bin/python3.11 -m pytest tests/ -q` stays green; no new hard deps.
- `goal_id`/`user_id` are opaque strings; `memory_serde` is lenient.
- Post-turn writes are best-effort/swallowed.
- One intentional Layer-7 change (`GoalStore.update_goal` + engine call), guarded by existing tests.
- Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Branch: `goal-persistence` (checked out; spec committed).

---

### Task 1: `Goal` ORM → JSONB payload

**Files:** Modify `infra/db/models/goals.py`; Test `tests/unit/infra/test_db_models.py`.

- [ ] **Step 1: Update the failing test** — replace `test_goal_model_has_status_and_user_scope` in `tests/unit/infra/test_db_models.py` with:

```python
def test_goal_model_has_status_and_user_scope():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.Goal(user_id="u1", goal_id="g1", status="active",
                          payload={"title": "run 5k"}))
    with session_scope(factory) as s:
        row = s.query(models.Goal).filter_by(goal_id="g1").one()
        assert row.status == "active" and row.payload["title"] == "run 5k"
        assert s.query(models.Goal).filter_by(status="active").count() == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_db_models.py::test_goal_model_has_status_and_user_scope -q`
Expected: FAIL — `TypeError: 'goal_id'/'payload' is an invalid keyword argument`.

- [ ] **Step 3: Rewrite `infra/db/models/goals.py`:**

```python
from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import UserScopedMixin

_JSONB = JSON().with_variant(JSONB, "postgresql")


class Goal(UserScopedMixin, Base):
    __tablename__ = "goal"
    goal_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="tentative")
    payload: Mapped[dict] = mapped_column(_JSONB)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_db_models.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add infra/db/models/goals.py tests/unit/infra/test_db_models.py
git commit -m "feat(infra): JSONB-payload goal model

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `GoalStore.update_goal` + engine persistence call

**Files:** Modify `backend/layer7_goals/goal_store.py`, `backend/layer7_goals/engine.py`; Test `tests/unit/infra/test_goal_store_update.py`.

- [ ] **Step 1: Write the failing test** — `tests/unit/infra/test_goal_store_update.py`:

```python
from backend.layer7_goals.goal_store import GoalStore
from backend.layer7_goals.schemas import Goal


def test_update_goal_replaces_by_id_and_appends_if_absent():
    store = GoalStore()
    g = Goal(goal_id="g1", title="old")
    store.add_goal(g)
    store.update_goal(Goal(goal_id="g1", title="new"))
    assert len(store.goals) == 1 and store.get("g1").title == "new"
    store.update_goal(Goal(goal_id="g2", title="fresh"))
    assert len(store.goals) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_goal_store_update.py -q`
Expected: FAIL — `AttributeError: 'GoalStore' object has no attribute 'update_goal'`.

- [ ] **Step 3: Add `update_goal`** to `backend/layer7_goals/goal_store.py`, immediately after `add_goal`:

```python
    def update_goal(self, goal: Goal) -> None:
        for i, g in enumerate(self.goals):
            if g.goal_id == goal.goal_id:
                self.goals[i] = goal
                return
        self.goals.append(goal)
```

Then in `backend/layer7_goals/engine.py`, in the SC-3 progress block, add the persistence call. Change:

```python
            progress_monitor.update_progress_score(top, progress_signal)
            top.last_mentioned_at = now
            out.goals_updated.append(top.goal_id)
```
to:
```python
            progress_monitor.update_progress_score(top, progress_signal)
            top.last_mentioned_at = now
            goal_store.update_goal(top)  # persist progress through the store (store-agnostic)
            out.goals_updated.append(top.goal_id)
```

- [ ] **Step 4: Run to verify it passes + Layer-7 regression**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_goal_store_update.py -q` → PASS.
Run: `.venv/bin/python -m pytest tests/ -q -k goal` → PASS (existing Layer-7 tests unaffected; `update_goal(top)` replaces the same object).

- [ ] **Step 5: Commit**

```bash
git add backend/layer7_goals/goal_store.py backend/layer7_goals/engine.py tests/unit/infra/test_goal_store_update.py
git commit -m "feat(layer7): GoalStore.update_goal + persist progress in run_goal_pipeline

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `PostgresGoalStore` + pipeline persistence

**Files:** Create `infra/db/goal_store.py`; Test `tests/unit/infra/test_postgres_goal_store.py`, `tests/unit/infra/test_goal_pipeline_persists.py`.

**Interfaces:** `PostgresGoalStore(session_factory, user_id)` implementing the Layer-7 `GoalStore` interface (`add_goal`/`get`/`load_by_status`/`update_goal`; inherits `get_relevant_goals`).

- [ ] **Step 1: Write the failing tests** — `tests/unit/infra/test_postgres_goal_store.py`:

```python
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer7_goals.schemas import Goal
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.goal_store import PostgresGoalStore


def _store(user="u1"):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresGoalStore(make_session_factory(engine), user)


def test_add_get_and_status_filter():
    store = _store()
    store.add_goal(Goal(goal_id="g1", title="run 5k", status="active"))
    store.add_goal(Goal(goal_id="g2", title="read more", status="paused"))
    assert store.get("g1").title == "run 5k"
    assert [g.goal_id for g in store.load_by_status(["active"])] == ["g1"]


def test_goal_id_upsert_and_update():
    store = _store()
    store.add_goal(Goal(goal_id="g1", title="v1", status="active"))
    store.update_goal(Goal(goal_id="g1", title="v2", status="active"))
    active = store.load_by_status(["active"])
    assert len(active) == 1 and active[0].title == "v2"


def test_cross_user_isolation():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    f = make_session_factory(engine)
    PostgresGoalStore(f, "u1").add_goal(Goal(goal_id="g1", title="a", status="active"))
    PostgresGoalStore(f, "u2").add_goal(Goal(goal_id="g2", title="b", status="active"))
    assert [g.title for g in PostgresGoalStore(f, "u1").load_by_status(["active"])] == ["a"]


def test_get_relevant_goals_inherited():
    store = _store()
    store.add_goal(Goal(goal_id="g1", title="run a 5k", status="active",
                        last_mentioned_at=datetime.now(timezone.utc)))
    rel = store.get_relevant_goals("let's talk about the 5k", similarity_fn=lambda a, b: 1.0)
    assert rel and rel[0].goal.goal_id == "g1"
```

`tests/unit/infra/test_goal_pipeline_persists.py`:

```python
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer7_goals import run_goal_pipeline
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.goal_store import PostgresGoalStore


def _factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def test_new_goal_extracted_and_persisted():
    f = _factory()
    now = datetime.now(timezone.utc)

    def fake_llm(_prompt):
        return {"goal_detected": True,
                "new_goal": {"inferred_title": "run a 5k", "confidence": 0.8}}

    out = run_goal_pipeline("I want to run a 5k next month",
                            goal_store=PostgresGoalStore(f, "u1"),
                            extractor_llm_fn=fake_llm, now=now)
    assert out.new_goals_created
    active = PostgresGoalStore(f, "u1").load_by_status(["active"])
    assert any(g.title == "run a 5k" for g in active)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_postgres_goal_store.py tests/unit/infra/test_goal_pipeline_persists.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'infra.db.goal_store'`.

- [ ] **Step 3: Implement `infra/db/goal_store.py`:**

```python
"""Postgres-backed Layer-7 GoalStore — a drop-in for the in-memory GoalStore.

Overrides the persistence methods (JSONB payload via memory_serde) and inherits get_relevant_goals,
which is expressed purely in terms of load_by_status + pure scoring.
"""
from __future__ import annotations

from backend.layer7_goals.goal_store import GoalStore
from backend.layer7_goals.schemas import Goal
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresGoalStore(GoalStore):
    def __init__(self, session_factory, user_id) -> None:
        super().__init__()
        self._sf = session_factory
        self._user_id = str(user_id)

    def _upsert(self, goal: Goal) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.Goal).filter_by(goal_id=str(goal.goal_id)).one_or_none()
            if row is None:
                s.add(m.Goal(user_id=str(goal.user_id or self._user_id),
                             goal_id=str(goal.goal_id), status=goal.status,
                             payload=to_jsonable(goal)))
            else:
                row.user_id = str(goal.user_id or self._user_id)
                row.status = goal.status
                row.payload = to_jsonable(goal)

    def add_goal(self, goal: Goal) -> None:
        goal.user_id = goal.user_id or self._user_id
        self._upsert(goal)

    def update_goal(self, goal: Goal) -> None:
        self._upsert(goal)

    def get(self, goal_id: str):
        with session_scope(self._sf) as s:
            row = s.query(m.Goal).filter_by(goal_id=str(goal_id)).one_or_none()
            return from_jsonable(Goal, row.payload) if row else None

    def load_by_status(self, statuses):
        with session_scope(self._sf) as s:
            rows = (s.query(m.Goal)
                    .filter(m.Goal.user_id == self._user_id, m.Goal.status.in_(list(statuses)))
                    .all())
            return [from_jsonable(Goal, r.payload) for r in rows]
```

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_postgres_goal_store.py tests/unit/infra/test_goal_pipeline_persists.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add infra/db/goal_store.py tests/unit/infra/test_postgres_goal_store.py tests/unit/infra/test_goal_pipeline_persists.py
git commit -m "feat(infra): PostgresGoalStore drop-in for Layer-7 GoalStore

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Post-turn goal writer + compose into build_app_state

**Files:** Modify `api/state.py`; Test `tests/unit/api/test_state.py`.

**Interfaces:** `make_goal_writer(session_factory, system1_client, embed_client) -> Callable`; `_chain_writers(*writers) -> Callable`.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/api/test_state.py`:

```python
def test_goal_writer_persists_extracted_goal():
    from infra.db.goal_store import PostgresGoalStore
    from api.state import make_goal_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class GoalLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return '{"goal_detected": true, "new_goal": {"inferred_title": "run a 5k", "confidence": 0.8}}'

    class GoalCtx(Ctx):
        message = "I want to run a 5k next month"

    make_goal_writer(factory, GoalLLM(), FakeLLM())(GoalCtx())
    active = PostgresGoalStore(factory, "local-user").load_by_status(["active"])
    assert any(g.title == "run a 5k" for g in active)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/api/test_state.py::test_goal_writer_persists_extracted_goal -q`
Expected: FAIL — `ImportError: cannot import name 'make_goal_writer'`.

- [ ] **Step 3: Add to `api/state.py`.** Extend the import block with:

```python
from backend.layer2_memory.embedding import cosine_similarity
from backend.layer7_goals import run_goal_pipeline
from infra.db.goal_store import PostgresGoalStore
```

Add these two functions (after `make_state_update_writer`):

```python
def _chain_writers(*writers) -> Callable:
    """Compose post-turn writers; each runs in its own try/except so one failure never blocks another."""
    def _run(ctx) -> None:
        for w in writers:
            try:
                w(ctx)
            except Exception:
                logger.exception("composed post-turn writer failed; turn already delivered")
    return _run


def make_goal_writer(session_factory, system1_client, embed_client) -> Callable:
    """Post-turn: run the real Layer-7 goal pipeline (extract + progress) against Postgres."""
    def _extractor_llm(prompt):
        return system1_client.complete(prompt)

    def _sim(a, b):
        return cosine_similarity(embed_client.embed([a])[0], embed_client.embed([b])[0])

    def _write(ctx) -> None:
        try:
            store = PostgresGoalStore(session_factory, ctx.user_id)
            run_goal_pipeline(
                getattr(ctx, "message", "") or "", goal_store=store,
                message_id=getattr(ctx, "session_id", "") or "",
                extractor_llm_fn=_extractor_llm, similarity_fn=_sim,
                now=getattr(ctx, "now", None) or datetime.now(timezone.utc))
        except Exception:
            logger.exception("goal writer failed; turn already delivered")
    return _write
```

In `build_app_state`, replace the `session_writer=make_state_update_writer(...)` argument by composing both writers:

```python
    store = PostgresGoalStore  # (unused placeholder line — do not add; see below)
```

Concretely, change the `steps = build_pipeline_steps(...)` block to:

```python
    store = PostgresMemoryStore(session_factory)
    threshold = config.get("memory", {}).get("reinforcement_similarity_threshold", 0.5)
    session_writer = _chain_writers(
        make_state_update_writer(store, llm_clients["embed"], session_factory, threshold),
        make_goal_writer(session_factory, llm_clients["system1"], llm_clients["embed"]))
    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=store, session_writer=session_writer)
```

(Delete the placeholder line — it is only a note that `PostgresMemoryStore` remains the memory store.)

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/api/test_state.py -q`
Expected: PASS (all, including the new goal-writer test).

- [ ] **Step 5: Commit**

```bash
git add api/state.py tests/unit/api/test_state.py
git commit -m "feat(api): post-turn goal writer composed alongside the memory writer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Docker test + docs + full gate

**Files:** Create `tests/integration_infra/test_goal_store_postgres.py`; Modify `CLAUDE.md`, spec status.

- [ ] **Step 1: Write the docker test** — `tests/integration_infra/test_goal_store_postgres.py`:

```python
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer7_goals import run_goal_pipeline
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.goal_store import PostgresGoalStore

pytestmark = pytest.mark.docker


def test_goal_pipeline_roundtrip_live(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    f = make_session_factory(engine)
    title = f"run-{uuid4()}"

    def fake_llm(_p):
        return {"goal_detected": True, "new_goal": {"inferred_title": title, "confidence": 0.9}}

    run_goal_pipeline("I want to " + title, goal_store=PostgresGoalStore(f, "itest"),
                      extractor_llm_fn=fake_llm, now=datetime.now(timezone.utc))
    assert any(g.title == title for g in PostgresGoalStore(f, "itest").load_by_status(["active"]))
```

- [ ] **Step 2: Run against live Postgres**

Run:
```bash
docker compose -f docker/docker-compose.yml up -d postgres
# reset dev schema if the goal table changed from a prior run (dev DB only; Alembic is #4):
POSTGRES_URL="postgresql+psycopg://nova:nova@127.0.0.1:5432/nova" .venv/bin/python -c "
from infra.db.engine import make_engine; from infra.db.base import Base; import infra.db.models
e=make_engine('postgresql+psycopg://nova:nova@127.0.0.1:5432/nova'); Base.metadata.drop_all(e)
import infra.db.engine as x; x.init_db(e)"
POSTGRES_URL="postgresql+psycopg://nova:nova@127.0.0.1:5432/nova" .venv/bin/python -m pytest tests/integration_infra/test_goal_store_postgres.py -q -m docker
```
Expected: PASS (auto-skips if Postgres unreachable).

- [ ] **Step 3: Docs** — in `CLAUDE.md` API Layer section, note the post-turn path now also runs the Layer-7 goal pipeline (`make_goal_writer`) against `PostgresGoalStore`, persisting extracted/updated goals; move Layer-7 goal state out of the deferred list (keep accountability-injection-into-generation, L4/L5/L11/L13 state, and Chroma ANN deferred). Set the spec `**Status:**` to `Implemented`.

- [ ] **Step 4: Full gate**

Run: `/usr/bin/python3.11 -m pytest tests/ -q` → green (goal sqlalchemy tests skip; nothing regresses).
Run: `.venv/bin/python -m pytest tests/ -q -m "not docker"` → all pass.

- [ ] **Step 5: Commit**

```bash
git add tests/integration_infra/test_goal_store_postgres.py CLAUDE.md docs/superpowers/specs/2026-07-05-goal-persistence-design.md
git commit -m "test+docs: live goal persistence + CLAUDE.md reconciliation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes (author)

- **Spec coverage:** §4.1 Goal ORM → Task 1; §4.2 update_goal + engine → Task 2; §4.3 PostgresGoalStore → Task 3; §4.4 goal writer + compose → Task 4; §7 tests → Tasks 1–5; §8 success criteria 1–4 → Tasks 3 (extract+persist), 3/2 (progress persist), 2 (Layer-7 regression), 5 (gates/docker).
- **Type consistency:** `make_goal_writer(session_factory, system1_client, embed_client)` and `_chain_writers(*writers)` used identically in defs and `build_app_state`. `PostgresGoalStore(session_factory, user_id)` consistent across tests + writer.
- **Inherited relevance:** `get_relevant_goals` is not overridden; it calls the overridden `load_by_status`, so Postgres data flows through the same ranking (test in Task 3 Step 1).
- **Layer-7 edit safety:** `update_goal(top)` replaces the same object already in the in-memory list (identity), so existing Layer-7 pipeline tests are unaffected (verified Task 2 Step 4).
