# Layer-2 Postgres Write Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the real Layer-2 `state_updater` in `/chat`'s post-turn path so reinforcement, UWM version-bump, and a tamper-evident audit chain all persist to Postgres and survive restarts.

**Architecture:** A new `PostgresAuditTrail` persists the SHA-256 audit chain to a JSONB-payload `memory_audit` table (continuing the chain across restarts). `state_updater` gains a one-line re-save so reinforced `S_current` persists through a Postgres store. A new post-turn writer computes similarity-gated `used_memory_ids` and drives the real `state_updater`.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x (JSONB), pytest, stdlib `hashlib`/`dataclasses`.

## Global Constraints

- Run sqlalchemy/pydantic tests with `.venv/bin/python -m pytest` (system `/usr/bin/python3.11` has no third-party deps).
- **Offline invariant:** `/usr/bin/python3.11 -m pytest tests/ -q` stays green; every sqlalchemy test starts `pytest.importorskip("sqlalchemy")`. No new hard dependencies.
- `user_id`/`session_id`/`memory_id` are opaque string keys; `memory_serde` decoding is lenient.
- Post-turn writes are best-effort and exception-swallowed — never affect the delivered response.
- Only one intentional Layer-2 change (the `state_updater` re-save + a public hash alias), guarded by existing tests.
- Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Branch: `layer2-write-path` (checked out; spec already committed).

---

### Task 1: `memory_audit` ORM → JSONB payload

**Files:**
- Modify: `infra/db/models/memory.py` (rewrite `MemoryAudit`)
- Test: `tests/unit/infra/test_db_models.py` (add a payload-shape test)

**Interfaces:**
- Produces `MemoryAudit(user_id, entry_hash[unique], prev_hash, event_type, payload)` on `Base.metadata`.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/infra/test_db_models.py`:

```python
def test_memory_audit_payload_shape():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.MemoryAudit(user_id="u1", entry_hash="h1", prev_hash=None,
                                 event_type="memory_created", payload={"reason": "x"}))
    with session_scope(factory) as s:
        row = s.query(models.MemoryAudit).filter_by(entry_hash="h1").one()
        assert row.event_type == "memory_created" and row.payload["reason"] == "x"
        assert row.prev_hash is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_db_models.py::test_memory_audit_payload_shape -q`
Expected: FAIL — `TypeError: 'payload' is an invalid keyword argument` (old model has `event`/`reason`).

- [ ] **Step 3: Rewrite `MemoryAudit`** in `infra/db/models/memory.py`. Replace the class with:

```python
class MemoryAudit(UserScopedMixin, Base):
    __tablename__ = "memory_audit"
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)
```

Then remove the now-unused `Text` from the top import line, changing:

```python
from sqlalchemy import Boolean, JSON, String, Text, UniqueConstraint
```
to:
```python
from sqlalchemy import Boolean, JSON, String, UniqueConstraint
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_db_models.py -q`
Expected: PASS (all tests, including the new one).

- [ ] **Step 5: Commit**

```bash
git add infra/db/models/memory.py tests/unit/infra/test_db_models.py
git commit -m "feat(infra): JSONB-payload memory_audit model

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `PostgresAuditTrail` (+ public hash function)

**Files:**
- Modify: `backend/layer2_memory/audit_trail.py` (expose `compute_event_hash`)
- Modify: `backend/layer2_memory/__init__.py` (export `compute_event_hash`)
- Create: `infra/db/audit_trail.py`
- Test: `tests/unit/infra/test_audit_trail_postgres.py`

**Interfaces:**
- Consumes: `MemoryAudit` (Task 1); `memory_serde`; `session_scope`.
- Produces: `compute_event_hash(event) -> str`; `PostgresAuditTrail(session_factory, user_id)` with `append(event) -> AuditEvent` and `verify() -> bool`.

- [ ] **Step 1: Expose the hash function** in `backend/layer2_memory/audit_trail.py` — rename `_compute_hash` to `compute_event_hash` and keep a backward-compatible alias. Change the `def _compute_hash(event: AuditEvent) -> str:` line to `def compute_event_hash(event: AuditEvent) -> str:`, and immediately after the function body add:

```python
_compute_hash = compute_event_hash  # backward-compatible internal alias
```

(The two internal call sites `_compute_hash(event)` inside `AuditTrail.append`/`verify` keep working via the alias.) Add `compute_event_hash` to the `from .audit_trail import ...` line in `backend/layer2_memory/__init__.py`:

```python
from .audit_trail import AuditTrail, compute_event_hash, detect_narrative_links
```

- [ ] **Step 2: Write the failing test** — `tests/unit/infra/test_audit_trail_postgres.py`:

```python
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer2_memory.schemas import AuditEvent, AuditEventType
from infra.db.engine import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.audit_trail import PostgresAuditTrail


def _factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def _event(reason):
    return AuditEvent(user_id="u1", timestamp=datetime.now(timezone.utc),
                      event_type=AuditEventType.MEMORY_CREATED, reason=reason,
                      triggered_by="test")


def test_append_builds_verifiable_chain():
    f = _factory()
    trail = PostgresAuditTrail(f, "u1")
    e1 = trail.append(_event("first"))
    e2 = trail.append(_event("second"))
    assert e1.content_hash and e2.prev_event_hash == e1.content_hash
    assert trail.verify() is True


def test_chain_continues_across_restart():
    f = _factory()
    PostgresAuditTrail(f, "u1").append(_event("first"))
    first_hash = PostgresAuditTrail(f, "u1")._head
    # A brand-new trail object over the same DB continues the chain.
    e2 = PostgresAuditTrail(f, "u1").append(_event("second"))
    assert e2.prev_event_hash == first_hash


def test_tampering_a_row_fails_verify():
    f = _factory()
    trail = PostgresAuditTrail(f, "u1")
    trail.append(_event("first"))
    trail.append(_event("second"))
    with session_scope(f) as s:
        row = s.query(models.MemoryAudit).order_by(models.MemoryAudit.id.asc()).first()
        payload = dict(row.payload)
        payload["reason"] = "tampered"
        row.payload = payload
    assert PostgresAuditTrail(f, "u1").verify() is False
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_audit_trail_postgres.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'infra.db.audit_trail'`.

- [ ] **Step 4: Implement `infra/db/audit_trail.py`:**

```python
"""Postgres-backed tamper-evident audit trail — a drop-in for Layer 2's AuditTrail.

Persists the SHA-256 hash chain to the ``memory_audit`` JSONB table. Constructed per user; loads
the last persisted ``entry_hash`` on init so the chain continues across process restarts.
"""
from __future__ import annotations

from backend.layer2_memory.audit_trail import GENESIS_HASH, compute_event_hash
from backend.layer2_memory.schemas import AuditEvent
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


def _event_type_value(event: AuditEvent) -> str:
    et = event.event_type
    return et.value if hasattr(et, "value") else str(et)


class PostgresAuditTrail:
    def __init__(self, session_factory, user_id) -> None:
        self._sf = session_factory
        self._user_id = str(user_id)
        self._head = self._load_head()

    def _load_head(self) -> str:
        with session_scope(self._sf) as s:
            row = (s.query(m.MemoryAudit).filter_by(user_id=self._user_id)
                   .order_by(m.MemoryAudit.id.desc()).first())
            return row.entry_hash if row else GENESIS_HASH

    def append(self, event: AuditEvent) -> AuditEvent:
        event.user_id = event.user_id or self._user_id
        event.prev_event_hash = self._head
        event.content_hash = compute_event_hash(event)
        with session_scope(self._sf) as s:
            s.add(m.MemoryAudit(
                user_id=self._user_id, entry_hash=event.content_hash,
                prev_hash=event.prev_event_hash, event_type=_event_type_value(event),
                payload=to_jsonable(event)))
        self._head = event.content_hash
        return event

    def verify(self) -> bool:
        with session_scope(self._sf) as s:
            payloads = [r.payload for r in
                        s.query(m.MemoryAudit).filter_by(user_id=self._user_id)
                        .order_by(m.MemoryAudit.id.asc()).all()]
        prev = GENESIS_HASH
        for p in payloads:
            event = from_jsonable(AuditEvent, p)
            if event.prev_event_hash != prev or event.content_hash != compute_event_hash(event):
                return False
            prev = event.content_hash
        return True
```

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_audit_trail_postgres.py -q`
Expected: PASS (3 passed). Also run `tests/ -k audit` in the venv to confirm the Layer-2 `AuditTrail` tests still pass after the rename:
`.venv/bin/python -m pytest tests/ -q -k audit` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/layer2_memory/audit_trail.py backend/layer2_memory/__init__.py \
        infra/db/audit_trail.py tests/unit/infra/test_audit_trail_postgres.py
git commit -m "feat(infra): PostgresAuditTrail — durable SHA-256 audit chain

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `state_updater` re-saves reinforced memories

**Files:**
- Modify: `backend/layer2_memory/state_updater.py` (add re-save)
- Test: `tests/unit/infra/test_state_updater_persists.py`

**Interfaces:**
- Consumes: `PostgresMemoryStore`, `PostgresAuditTrail` (Task 2), `state_updater`.

- [ ] **Step 1: Write the failing test** — `tests/unit/infra/test_state_updater_persists.py`:

```python
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer2_memory import state_updater
from backend.layer2_memory.schemas import (
    EpisodicMemory, EmotionVector, ScoredMemory, ShortTermMemoryBuffer,
)
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail


def _ctx():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    f = make_session_factory(engine)
    return PostgresMemoryStore(f), PostgresAuditTrail(f, "u1")


def _no_new_episodes(_stm, _emotion):
    return []


def test_reinforced_memory_strength_persists():
    store, audit = _ctx()
    now = datetime.now(timezone.utc)
    mem = EpisodicMemory(user_id="u1", summary="loves hiking",
                         embedding=[0.1, 0.2], S_current=0.5, importance_score=0.6,
                         created_at=now)
    store.save_episodic(mem)
    scored = ScoredMemory(memory=mem, effective_score=0.9)
    stm = ShortTermMemoryBuffer(session_id="s1", user_id="u1")
    state_updater("u1", "s1", stm, store, audit, EmotionVector(), now, _no_new_episodes,
                  last_recall=[scored], used_memory_ids={mem.memory_id})
    reloaded = store.get_episodic(mem.memory_id)
    assert reloaded.S_current > 0.5           # reinforced AND persisted through the store
    assert reloaded.reinforcement_count == 1
    assert audit.verify() is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_state_updater_persists.py -q`
Expected: FAIL — `reloaded.S_current > 0.5` is False (in-place mutation didn't write through the Postgres store).

- [ ] **Step 3: Add the re-save** in `backend/layer2_memory/state_updater.py`. Change the reinforcement block (currently):

```python
            mem.S_current = ms.reinforce(mem.S_current, signal)
            mem.reinforcement_count += 1
            result.memories_reinforced += 1
```
to:
```python
            mem.S_current = ms.reinforce(mem.S_current, signal)
            mem.reinforcement_count += 1
            store.save_episodic(mem)  # persist strength through the store (store-agnostic)
            result.memories_reinforced += 1
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/infra/test_state_updater_persists.py -q`
Expected: PASS.
Then confirm the existing Layer-2 state_updater tests still pass:
`.venv/bin/python -m pytest tests/ -q -k state_updater` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/layer2_memory/state_updater.py tests/unit/infra/test_state_updater_persists.py
git commit -m "fix(layer2): state_updater re-saves reinforced memories (store-agnostic)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Similarity-gate helper + config threshold

**Files:**
- Modify: `config/defaults.yaml` (add `memory.reinforcement_similarity_threshold`)
- Create: `api/reinforcement.py` (pure helper)
- Test: `tests/unit/api/test_reinforcement_gate.py`

**Interfaces:**
- Produces: `used_memory_ids(response_embedding: list[float], scored_memories: list, threshold: float) -> set` — memory_ids of recalled memories whose embedding is within `threshold` cosine of the response.

- [ ] **Step 1: Add the config key** — in `config/defaults.yaml`, under the `memory:` block, add a line after `decay_rate: 0.92`:

```yaml
  reinforcement_similarity_threshold: 0.5
```

- [ ] **Step 2: Write the failing test** — `tests/unit/api/test_reinforcement_gate.py`:

```python
from backend.layer2_memory import DeterministicEmbedder
from backend.layer2_memory.schemas import EpisodicMemory, ScoredMemory
from api.reinforcement import used_memory_ids


def test_gate_includes_reflected_excludes_unreflected():
    emb = DeterministicEmbedder()
    hiking = EpisodicMemory(user_id="u1", summary="loves hiking in the mountains",
                            embedding=emb.embed("loves hiking in the mountains"))
    cooking = EpisodicMemory(user_id="u1", summary="bakes sourdough bread at home",
                             embedding=emb.embed("bakes sourdough bread at home"))
    scored = [ScoredMemory(memory=hiking), ScoredMemory(memory=cooking)]
    resp = emb.embed("we talked about hiking in the mountains today")
    used = used_memory_ids(resp, scored, threshold=0.1)
    assert hiking.memory_id in used
    assert cooking.memory_id not in used


def test_gate_empty_response_embedding_returns_empty():
    assert used_memory_ids([], [], threshold=0.5) == set()
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/api/test_reinforcement_gate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.reinforcement'`.

- [ ] **Step 4: Implement `api/reinforcement.py`:**

```python
"""Similarity gate: decide which recalled memories the response actually 'used'.

Realizes state_updater's "reinforce memories actually used in the response" contract without LLM
attribution — a recalled memory is 'used' if its embedding is within ``threshold`` cosine of the
response embedding.
"""
from __future__ import annotations

from backend.layer2_memory.embedding import cosine_similarity


def used_memory_ids(response_embedding, scored_memories, threshold: float) -> set:
    used = set()
    if not response_embedding:
        return used
    for sm in scored_memories:
        mem = getattr(sm, "memory", None)
        emb = getattr(mem, "embedding", None) if mem is not None else None
        if emb and cosine_similarity(response_embedding, emb) >= threshold:
            used.add(mem.memory_id)
    return used
```

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/api/test_reinforcement_gate.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add config/defaults.yaml api/reinforcement.py tests/unit/api/test_reinforcement_gate.py
git commit -m "feat(api): similarity gate for reinforcement (used-in-response)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Wire the real `state_updater` into the post-turn path

**Files:**
- Modify: `api/state.py` (replace `make_episodic_writer` with `make_state_update_writer`; use it in `build_app_state`)
- Test: `tests/unit/api/test_state.py` (replace the writer tests)

**Interfaces:**
- Consumes: `PostgresMemoryStore`, `PostgresAuditTrail`, `used_memory_ids`, `state_updater`, `EpisodicMemory`/`EmotionVector`/`ShortTermMemoryBuffer`.
- Produces: `make_state_update_writer(store, embed_client, session_factory, threshold) -> Callable`.

- [ ] **Step 1: Write the failing test** — replace `tests/unit/api/test_state.py` with:

```python
import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from datetime import datetime, timezone

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail
from backend.layer2_memory.schemas import EpisodicMemory, ScoredMemory
from api.state import build_app_state, make_state_update_writer


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "hi there"
    def stream(self, prompt, **k):
        yield "hi there"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _sqlite_state():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    return build_app_state(config={"system": {"default_user_id": "local-user"},
                                   "llm": {}, "memory": {}},
                           llm_clients=clients, engine=engine, vector_store=object())


class Ctx:
    user_id = "local-user"
    session_id = "s1"
    message = "hey there"
    now = datetime.now(timezone.utc)
    response_text = "loves hiking"
    emotion_intent = None
    recalled_memories = []


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_writer_persists_episode_session_and_audit():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1)(Ctx())
    assert any(m.summary == "hey there" for m in store.active_episodic("local-user"))
    with session_scope(factory) as s:
        assert s.query(models.Session).filter_by(session_key="s1").one().turn_count == 1
    assert PostgresAuditTrail(factory, "local-user").verify() is True


def test_writer_reinforces_similarity_matched_recalled_memory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="loves hiking",
                         embedding=[0.1, 0.2, 0.3], S_current=0.5,
                         created_at=datetime.now(timezone.utc))
    store.save_episodic(mem)

    class C(Ctx):
        recalled_memories = [ScoredMemory(memory=mem, effective_score=0.9)]
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1)(C())
    assert store.get_episodic(mem.memory_id).S_current > 0.5
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/api/test_state.py -q`
Expected: FAIL — `ImportError: cannot import name 'make_state_update_writer'`.

- [ ] **Step 3: Replace the writer** in `api/state.py`. Update the import block to add the new names:

```python
from datetime import datetime, timezone

from config import load_config
from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail
from backend.layer2_memory import state_updater
from backend.layer2_memory.schemas import EpisodicMemory, EmotionVector, ShortTermMemoryBuffer
from backend.pipeline import ConversationOrchestrator
from api.assembly import build_pipeline_steps
from api.reinforcement import used_memory_ids
```

Replace the entire `make_episodic_writer` function with:

```python
def make_state_update_writer(store, embed_client, session_factory, threshold: float) -> Callable:
    """Post-turn writer that runs the real Layer-2 state_updater against Postgres.

    Upserts the Session turn count, then extracts a new episode from the turn, reinforces the
    recalled memories the response actually reflected (similarity-gated), bumps the UWM version if
    present, and appends a persisted audit event for each — all durable across restarts. Best-effort
    and swallowed: the response is already delivered.
    """
    def _write(ctx) -> None:
        try:
            key = getattr(ctx, "session_id", "") or "default"
            with session_scope(session_factory) as s:
                row = s.query(models.Session).filter_by(session_key=key).one_or_none()
                if row is None:
                    s.add(models.Session(user_id=ctx.user_id, session_key=key, turn_count=1))
                else:
                    row.turn_count += 1

            now = getattr(ctx, "now", None) or datetime.now(timezone.utc)
            message = getattr(ctx, "message", "") or ""
            response = getattr(ctx, "response_text", "") or ""
            recalled = getattr(ctx, "recalled_memories", []) or []
            used = used_memory_ids(embed_client.embed([response])[0], recalled, threshold) \
                if response else set()

            def _extractor(_stm, _emotion):
                if not message:
                    return []
                return [EpisodicMemory(
                    user_id=ctx.user_id, summary=message[:2000],
                    embedding=embed_client.embed([message])[0], created_at=now,
                    importance_score=0.3, S_current=1.0, creation_agent="api.state_update")]

            stm = ShortTermMemoryBuffer(session_id=key, user_id=ctx.user_id)
            audit = PostgresAuditTrail(session_factory, ctx.user_id)
            state_updater(ctx.user_id, key, stm, store, audit, EmotionVector(), now, _extractor,
                          last_recall=recalled, used_memory_ids=used)
        except Exception:
            logger.exception("state-update writer failed; turn already delivered")
    return _write
```

In `build_app_state`, replace the `store = ...` / `steps = build_pipeline_steps(...)` block with:

```python
    store = PostgresMemoryStore(session_factory)
    threshold = config.get("memory", {}).get("reinforcement_similarity_threshold", 0.5)
    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=store,
        session_writer=make_state_update_writer(store, llm_clients["embed"],
                                                session_factory, threshold))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/api/test_state.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add api/state.py tests/unit/api/test_state.py
git commit -m "feat(api): drive real state_updater post-turn (reinforce + audit persist)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Docker integration test (live Postgres)

**Files:**
- Create: `tests/integration_infra/test_audit_trail_postgres.py`

**Interfaces:**
- Consumes: `PostgresMemoryStore`, `PostgresAuditTrail`, `state_updater`; `postgres_url` fixture.

- [ ] **Step 1: Write the test:**

```python
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory import state_updater
from backend.layer2_memory.schemas import (
    EpisodicMemory, EmotionVector, ScoredMemory, ShortTermMemoryBuffer,
)
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail

pytestmark = pytest.mark.docker


def test_reinforce_and_audit_roundtrip_live(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    f = make_session_factory(engine)
    store, audit = PostgresMemoryStore(f), PostgresAuditTrail(f, "itest")
    now = datetime.now(timezone.utc)
    mem = EpisodicMemory(user_id="itest", summary=f"live-{uuid4()}",
                         embedding=[0.1, 0.2], S_current=0.5, created_at=now)
    store.save_episodic(mem)
    scored = ScoredMemory(memory=mem, effective_score=0.9)
    stm = ShortTermMemoryBuffer(session_id="s1", user_id="itest")
    state_updater("itest", "s1", stm, store, audit, EmotionVector(), now,
                  lambda _s, _e: [], last_recall=[scored], used_memory_ids={mem.memory_id})
    assert store.get_episodic(mem.memory_id).S_current > 0.5
    assert audit.verify() is True
```

- [ ] **Step 2: Run against live Postgres**

Run:
```bash
docker compose -f docker/docker-compose.yml up -d postgres
POSTGRES_URL="postgresql+psycopg://nova:nova@127.0.0.1:5432/nova" \
  .venv/bin/python -m pytest tests/integration_infra/test_audit_trail_postgres.py -q -m docker
```
Expected: PASS (auto-skips if Postgres is unreachable or deps absent). Note: if the live DB has a stale `memory_audit` schema from a prior run, reset it with `Base.metadata.drop_all(engine); init_db(engine)` (dev DB only — Alembic is increment #4).

- [ ] **Step 3: Commit**

```bash
git add tests/integration_infra/test_audit_trail_postgres.py
git commit -m "test(infra): docker reinforce+audit roundtrip against live Postgres

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Docs reconciliation + full-suite gate

**Files:**
- Modify: `CLAUDE.md` (API Layer section)
- Modify: `docs/superpowers/specs/2026-07-05-layer2-write-path-persistence-design.md` (Status → Implemented)

- [ ] **Step 1: Update CLAUDE.md** — in the "### API Layer (`api/`)" section, update the write-path sentence: the post-turn path now runs the **real Layer-2 `state_updater`** (via `make_state_update_writer`), persisting a new episode, similarity-gated reinforcement (`S_current` write-back), UWM version-bump, and a durable SHA-256 audit chain (`PostgresAuditTrail`, `infra/db/audit_trail.py`). Move "reinforcement/UWM/audit write-back" **out** of the deferred list; keep Chroma ANN, per-user Layer 4/5/7/11/13 state, and Alembic deferred. Reference `docs/superpowers/specs/2026-07-05-layer2-write-path-persistence-design.md`.

- [ ] **Step 2: Update the spec status** — change `**Status:** Approved (design)` to `**Status:** Implemented`.

- [ ] **Step 3: Full offline gate**

Run: `/usr/bin/python3.11 -m pytest tests/ -q`
Expected: green with only importorskip/docker skips; count increased vs. before, nothing regressed.
Then the venv true-pass gate: `.venv/bin/python -m pytest tests/ -q -m "not docker"` → all pass.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-07-05-layer2-write-path-persistence-design.md
git commit -m "docs: reconcile CLAUDE.md + spec status for Layer-2 write path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes (author)

- **Spec coverage:** §3.1 memory_audit model → Task 1; §3.2 PostgresAuditTrail + public hash → Task 2; §3.3 state_updater re-save → Task 3; §3.4 similarity gate + config → Task 4; §3.5 make_state_update_writer + wiring → Task 5; §6 testing → Tasks 1–6; §7 success criteria 1–4 → Tasks 2 (chain+restart), 3/5 (reinforce+persist), 5 (episode), 7 (gates).
- **Type consistency:** `make_state_update_writer(store, embed_client, session_factory, threshold)` and `used_memory_ids(response_embedding, scored_memories, threshold)` used identically in defs and call sites. `compute_event_hash` defined in Task 2, consumed by `PostgresAuditTrail`.
- **Opaque ids:** `state_updater` is called with string `user_id`/`session_id`; the dataclass UUID annotations are advisory and `memory_serde` is lenient (established PR #19).
- **Emotion:** neutral `EmotionVector()` is passed (the injected extractor ignores emotion and no UWM emotion enrichment is in scope) — documented simplification, matches spec §3.5.
