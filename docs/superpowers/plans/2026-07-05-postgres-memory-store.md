# PostgresMemoryStore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Layer 2 a Postgres-backed memory store that is a literal drop-in for `InMemoryMemoryStore`, so `/chat` accumulates recallable episodic memories that survive a process restart.

**Architecture:** A generic recursive dataclass↔JSON codec (`memory_serde`) round-trips the rich Layer-2 memory dataclasses into a JSONB `payload` column; the three thin memory ORM models are rewritten to `payload` + a few promoted, indexed query columns, and a new `user_world_model` table is added. `PostgresMemoryStore` implements the exact Layer-2 store interface over that schema. `build_app_state` swaps `InMemoryMemoryStore` for it and wires a real post-turn episodic write.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x (`JSON().with_variant(JSONB, "postgresql")`), pytest, stdlib `dataclasses`/`typing`/`uuid`/`datetime`.

## Global Constraints

- Test runner: `/usr/bin/python3.11 -m pytest` (system interpreter has **no** third-party deps installed).
- **Offline invariant:** `/usr/bin/python3.11 -m pytest tests/ -q` must stay green on the bare interpreter. Every test that imports `sqlalchemy` starts with `pytest.importorskip("sqlalchemy")`; the pure codec tests import no third-party packages.
- **No new hard dependencies.** SQLAlchemy is already the `infra` extra; nothing new is added.
- `user_id` is an **opaque string key** end-to-end; the Layer-2 dataclass `UUID` annotation is advisory. The codec must not coerce non-UUID id strings.
- **No changes to Layer-2 consumers** (arbiter, recall engine, state_updater). The one permitted Layer-2 edit is a behavior-preserving refactor of `memory_store.py` (extracting the UWM query helper), guarded by existing tests.
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Branch: `postgres-memory-store` (already checked out; spec already committed).

---

### Task 1: Generic dataclass↔JSON codec

**Files:**
- Create: `infra/db/memory_serde.py`
- Test: `tests/unit/infra/test_memory_serde.py`

**Interfaces:**
- Consumes: Layer-2 dataclasses from `backend.layer2_memory.schemas`.
- Produces:
  - `to_jsonable(obj: Any) -> Any` — dataclass tree → JSON-native primitives.
  - `from_jsonable(tp: Any, data: Any) -> Any` — rebuild a typed value of target type `tp` from JSON-native data. Lenient UUID decoding: an id string that isn't a valid UUID is returned unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/test_memory_serde.py
from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory.schemas import (
    EpisodicMemory, IdentityMemory, SemanticMemory, UserWorldModel,
    EmotionVector, PersonNode, RecallEvent,
)
from infra.db.memory_serde import to_jsonable, from_jsonable


def _roundtrip(tp, obj):
    return from_jsonable(tp, to_jsonable(obj))


def test_episodic_roundtrip_full_fidelity():
    m = EpisodicMemory(
        user_id=uuid4(), session_id=uuid4(), summary="hiking trip",
        embedding=[0.1, 0.2, 0.3], topic_tags=["outdoors"], created_at=datetime.now(timezone.utc),
        emotion_vector=EmotionVector(valence=0.4, arousal=0.2, dominant_label="joy"),
        S_current=0.8, decay_rate=0.01, reinforcement_count=2,
        recall_history=[RecallEvent(recalled_at=datetime.now(timezone.utc), trigger_query="q")],
        source_turn_ids=[uuid4()], is_archived=False, is_deleted=False)
    assert _roundtrip(EpisodicMemory, m) == m


def test_semantic_and_identity_roundtrip():
    s = SemanticMemory(user_id=uuid4(), statement="likes tea", confidence=0.7, evidence_count=3)
    assert _roundtrip(SemanticMemory, s) == s
    i = IdentityMemory(statement="values honesty", is_immutable=True, centrality=0.9)
    assert _roundtrip(IdentityMemory, i) == i


def test_uwm_deep_nesting_roundtrip():
    uwm = UserWorldModel(user_id=uuid4())
    uwm.relationship_graph.people.append(PersonNode(name="Sam", aliases=["Sammy"], mention_count=4))
    uwm.confidence_by_field["profile"] = 0.5
    assert _roundtrip(UserWorldModel, uwm) == uwm


def test_uuid_decoding_is_lenient_for_opaque_string_ids():
    # The pipeline uses a string user_id ("local-user"); the dataclass annotates UUID.
    from uuid import UUID
    from typing import Optional
    assert from_jsonable(Optional[UUID], "local-user") == "local-user"
    real = uuid4()
    assert from_jsonable(UUID, str(real)) == real


def test_missing_fields_fall_back_to_defaults():
    m = from_jsonable(EpisodicMemory, {"summary": "partial"})
    assert m.summary == "partial" and m.embedding == [] and m.reinforcement_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_memory_serde.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'infra.db.memory_serde'`

- [ ] **Step 3: Write minimal implementation**

```python
# infra/db/memory_serde.py
"""Generic JSON codec for Layer-2 memory dataclasses.

`to_jsonable` turns any dataclass tree into JSON-native primitives; `from_jsonable`
rebuilds a typed dataclass from that tree, driven by the target type's annotations. This is
the fidelity guarantee for PostgresMemoryStore: `from_jsonable(T, to_jsonable(x)) == x`.

UUID decoding is deliberately lenient: an id string that is not a valid UUID (e.g. the
pipeline's "local-user") is returned unchanged, matching the design decision that ids are
opaque keys and the dataclass `UUID` annotation is advisory.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

_HINTS_CACHE: dict[type, dict[str, Any]] = {}


def _hints(cls: type) -> dict[str, Any]:
    if cls not in _HINTS_CACHE:
        _HINTS_CACHE[cls] = get_type_hints(cls)
    return _HINTS_CACHE[cls]


def to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if dataclasses.is_dataclass(obj):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    raise TypeError(f"cannot serialize {type(obj)!r}")


def _unwrap_optional(tp: Any) -> Any:
    if get_origin(tp) is Union:
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def from_jsonable(tp: Any, data: Any) -> Any:
    if data is None:
        return None
    tp = _unwrap_optional(tp)
    origin = get_origin(tp)
    if origin in (list, tuple):
        args = get_args(tp)
        item_tp = args[0] if args else Any
        return [from_jsonable(item_tp, x) for x in data]
    if origin is dict:
        return dict(data)
    if dataclasses.is_dataclass(tp):
        hints = _hints(tp)
        return tp(**{f.name: from_jsonable(hints[f.name], data[f.name])
                     for f in dataclasses.fields(tp) if f.name in data})
    if isinstance(tp, type) and issubclass(tp, Enum):
        return tp(data)
    if tp is UUID:
        try:
            return UUID(data)
        except (ValueError, AttributeError, TypeError):
            return data  # opaque string id — keep as-is (advisory UUID annotation)
    if tp is datetime:
        return datetime.fromisoformat(data)
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_memory_serde.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add infra/db/memory_serde.py tests/unit/infra/test_memory_serde.py
git commit -m "feat(infra): generic dataclass<->JSON codec for Layer-2 memories

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: JSONB-payload ORM models + UWM table

**Files:**
- Modify: `infra/db/models/memory.py` (rewrite the three memory models; keep `MemoryAudit`; add `UserWorldModel`)
- Modify: `infra/db/models/__init__.py` (export `UserWorldModel`)
- Test: `tests/unit/infra/test_db_models.py` (update `EXPECTED_TABLES` + roundtrip test)

**Interfaces:**
- Produces ORM classes on `Base.metadata`:
  - `EpisodicMemory(user_id, memory_id[unique], is_deleted, is_archived, vector_id, payload)`
  - `SemanticMemory(user_id, memory_id[unique], is_deprecated, payload)`
  - `IdentityMemory(belief_id[unique], is_immutable, payload)` — cross-user (`TimestampMixin` only)
  - `UserWorldModel(user_id[unique], payload)`
  - `MemoryAudit` — unchanged
  - `payload` column type: `JSON().with_variant(JSONB, "postgresql")`

- [ ] **Step 1: Write the failing test**

Replace the body of `tests/unit/infra/test_db_models.py` with:

```python
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime

from infra.db.base import Base
from infra.db.engine import make_engine, make_session_factory, session_scope, init_db
import infra.db.models as models


EXPECTED_TABLES = {
    "session", "episodic_memory", "semantic_memory", "identity_memory", "memory_audit",
    "user_world_model", "persona_state", "relationship_state", "goal", "proactive_item",
    "safety_event", "privacy_audit", "longitudinal_summary", "tool_action", "output_pref",
    "onboarding_state",
}


def test_all_tables_registered():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_episodic_payload_roundtrip():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.EpisodicMemory(user_id="u1", memory_id="m1",
                                    payload={"summary": "first chat"}))
    with session_scope(factory) as s:
        row = s.query(models.EpisodicMemory).filter_by(memory_id="m1").one()
        assert row.payload["summary"] == "first chat"
        assert row.is_deleted is False and row.is_archived is False
        assert isinstance(row.created_at, datetime)


def test_user_world_model_one_per_user():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.UserWorldModel(user_id="u1", payload={"update_version": 0}))
    with session_scope(factory) as s:
        assert s.query(models.UserWorldModel).filter_by(user_id="u1").one().payload["update_version"] == 0


def test_goal_model_has_status_and_user_scope():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        s.add(models.Goal(user_id="u1", description="run 5k", status="active"))
    with session_scope(factory) as s:
        assert s.query(models.Goal).filter_by(status="active").count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_db_models.py -q`
Expected: FAIL — `AttributeError: ... has no attribute 'UserWorldModel'` / `TypeError` on `payload=`.

- [ ] **Step 3: Write minimal implementation**

Replace `infra/db/models/memory.py` with:

```python
from __future__ import annotations

from sqlalchemy import Boolean, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infra.db.base import Base
from infra.db.models._mixins import TimestampMixin, UserScopedMixin

# Real JSONB in Postgres; TEXT-backed JSON on SQLite (keeps the offline suite dependency-free).
_JSONB = JSON().with_variant(JSONB, "postgresql")


class EpisodicMemory(UserScopedMixin, Base):
    __tablename__ = "episodic_memory"
    memory_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Chroma link (later)
    payload: Mapped[dict] = mapped_column(_JSONB)


class SemanticMemory(UserScopedMixin, Base):
    __tablename__ = "semantic_memory"
    memory_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    payload: Mapped[dict] = mapped_column(_JSONB)


class IdentityMemory(TimestampMixin, Base):
    __tablename__ = "identity_memory"
    belief_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(_JSONB)


class UserWorldModel(UserScopedMixin, Base):
    __tablename__ = "user_world_model"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_world_model_user_id"),)
    payload: Mapped[dict] = mapped_column(_JSONB)


class MemoryAudit(UserScopedMixin, Base):
    __tablename__ = "memory_audit"
    event: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64))
```

Then update `infra/db/models/__init__.py`: add `UserWorldModel` to the `from .memory import (...)` line and to `__all__` (keep alphabetization consistent with the existing file). Example — change the memory import to:

```python
from .memory import (
    EpisodicMemory,
    IdentityMemory,
    MemoryAudit,
    SemanticMemory,
    UserWorldModel,
)
```

and add `"UserWorldModel",` to `__all__`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_db_models.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add infra/db/models/memory.py infra/db/models/__init__.py tests/unit/infra/test_db_models.py
git commit -m "feat(infra): JSONB-payload memory models + user_world_model table

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: PostgresMemoryStore + shared UWM query helper

**Files:**
- Modify: `backend/layer2_memory/memory_store.py` (extract `resolve_uwm_query`; delegate from `InMemoryMemoryStore.query_uwm` — behavior-preserving)
- Modify: `backend/layer2_memory/__init__.py` (export `resolve_uwm_query`)
- Create: `infra/db/memory_store.py`
- Test: `tests/unit/infra/test_postgres_memory_store.py`

**Interfaces:**
- Consumes: `to_jsonable`/`from_jsonable` (Task 1); ORM models (Task 2); `session_scope`; `resolve_uwm_query`.
- Produces: `PostgresMemoryStore(session_factory)` implementing the full Layer-2 store interface:
  `save_episodic · get_episodic · all_episodic · active_episodic · save_semantic · active_semantic · save_identity · identity_beliefs · candidate_memories · save_uwm · load_uwm · query_uwm`.
- Produces: `resolve_uwm_query(uwm, query_type, context="") -> dict` in `backend.layer2_memory`.

- [ ] **Step 1a: Refactor the UWM query helper (behavior-preserving)**

In `backend/layer2_memory/memory_store.py`, add a module-level function (move the exact branch logic out of `InMemoryMemoryStore.query_uwm`):

```python
def resolve_uwm_query(uwm, query_type: str, context: str = "") -> dict:
    """Typed UWM query logic shared by every store implementation (§7.9)."""
    if query_type == "relationship_context":
        if uwm is None:
            return {"relevant_people": []}
        ctx = context.lower()
        people = [
            p for p in uwm.relationship_graph.people
            if p.name.lower() in ctx or any(a.lower() in ctx for a in p.aliases)
        ]
        return {"relevant_people": people}
    if query_type == "active_stressors":
        if uwm is None:
            return {"active_stressors": []}
        return {"active_stressors": uwm.life_context.active_stressors}
    if query_type == "communication_preferences":
        if uwm is None:
            return {"communication_preferences": None}
        return {"communication_preferences": uwm.communication_model}
    if query_type == "psychological_posture":
        if uwm is None:
            return {"support_style": None, "triggers": []}
        return {
            "support_style": uwm.psychological_model.preferred_support_style,
            "triggers": uwm.psychological_model.known_triggers,
        }
    if query_type == "life_stage_context":
        if uwm is None:
            return {"profile": None, "active_situations": []}
        return {
            "profile": uwm.profile,
            "active_situations": uwm.life_context.active_situations,
        }
    return {}  # pragma: no cover - unknown query type
```

Then replace `InMemoryMemoryStore.query_uwm`'s body with a one-line delegation:

```python
    def query_uwm(self, user_id: UUID, query_type: str, context: str = "") -> dict:
        """Typed UWM query interface (§7.9). Downstream layers never touch the UWM directly."""
        return resolve_uwm_query(self._uwm.get(user_id), query_type, context)
```

Add `resolve_uwm_query` to the `from .memory_store import ...` line in `backend/layer2_memory/__init__.py`.

- [ ] **Step 1b: Verify the refactor didn't change Layer-2 behavior**

Run: `/usr/bin/python3.11 -m pytest tests/ -q -k "memory_store or arbiter or uwm"`
Expected: PASS (existing Layer-2 tests still green — this proves the extraction is behavior-preserving).

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/infra/test_postgres_memory_store.py
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory.schemas import (
    EpisodicMemory, SemanticMemory, IdentityMemory, UserWorldModel, PersonNode,
)
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore


def _store():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresMemoryStore(make_session_factory(engine))


def test_episodic_save_get_and_active_filtering():
    store = _store()
    live = EpisodicMemory(user_id="u1", summary="live", created_at=datetime.now(timezone.utc))
    dead = EpisodicMemory(user_id="u1", summary="dead", is_deleted=True)
    arch = EpisodicMemory(user_id="u1", summary="arch", is_archived=True)
    for m in (live, dead, arch):
        store.save_episodic(m)
    assert store.get_episodic(live.memory_id).summary == "live"
    assert {m.summary for m in store.active_episodic("u1")} == {"live"}
    assert len(store.all_episodic("u1")) == 3


def test_cross_user_isolation():
    store = _store()
    store.save_episodic(EpisodicMemory(user_id="u1", summary="a"))
    store.save_episodic(EpisodicMemory(user_id="u2", summary="b"))
    assert {m.summary for m in store.active_episodic("u1")} == {"a"}


def test_memory_id_upsert_replaces_not_duplicates():
    store = _store()
    m = EpisodicMemory(user_id="u1", summary="v1")
    store.save_episodic(m)
    m.summary = "v2"
    m.S_current = 0.5
    store.save_episodic(m)
    active = store.active_episodic("u1")
    assert len(active) == 1 and active[0].summary == "v2" and active[0].S_current == 0.5


def test_semantic_active_and_candidates():
    store = _store()
    store.save_semantic(SemanticMemory(user_id="u1", statement="s-live"))
    store.save_semantic(SemanticMemory(user_id="u1", statement="s-dead", is_deprecated=True))
    store.save_episodic(EpisodicMemory(user_id="u1", summary="e-live"))
    assert {s.statement for s in store.active_semantic("u1")} == {"s-live"}
    assert len(store.candidate_memories("u1")) == 2  # 1 episodic + 1 semantic


def test_identity_is_cross_user():
    store = _store()
    store.save_identity(IdentityMemory(statement="values honesty", is_immutable=True))
    beliefs = store.identity_beliefs()
    assert len(beliefs) == 1 and beliefs[0].statement == "values honesty"


def test_uwm_save_load_and_query():
    store = _store()
    uid = uuid4()
    uwm = UserWorldModel(user_id=uid)
    uwm.relationship_graph.people.append(PersonNode(name="Sam", aliases=["Sammy"]))
    store.save_uwm(uwm)
    loaded = store.load_uwm(str(uid))
    assert loaded is not None and loaded.relationship_graph.people[0].name == "Sam"
    res = store.query_uwm(str(uid), "relationship_context", "talking to Sammy today")
    assert [p.name for p in res["relevant_people"]] == ["Sam"]
    assert store.load_uwm("nobody") is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_postgres_memory_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'infra.db.memory_store'`

- [ ] **Step 4: Write minimal implementation**

```python
# infra/db/memory_store.py
"""Postgres-backed Layer-2 memory store — a drop-in for InMemoryMemoryStore.

Rich Layer-2 memory dataclasses are round-tripped through a JSONB `payload` column via
`memory_serde`; a few promoted, indexed columns carry the fields the read path filters on.
Every method opens a short-lived `session_scope`; ORM rows never escape the store (callers
only ever see reconstructed dataclasses).
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from backend.layer2_memory.memory_store import resolve_uwm_query
from backend.layer2_memory.schemas import (
    EpisodicMemory, IdentityMemory, Memory, SemanticMemory, UserWorldModel,
)
import infra.db.models as m
from infra.db.engine import session_scope
from infra.db.memory_serde import from_jsonable, to_jsonable


class PostgresMemoryStore:
    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    # ── Episodic ─────────────────────────────────────────────────────────
    def save_episodic(self, memory: EpisodicMemory) -> UUID:
        with session_scope(self._sf) as s:
            row = s.query(m.EpisodicMemory).filter_by(memory_id=str(memory.memory_id)).one_or_none()
            if row is None:
                s.add(m.EpisodicMemory(
                    user_id=str(memory.user_id), memory_id=str(memory.memory_id),
                    is_deleted=memory.is_deleted, is_archived=memory.is_archived,
                    payload=to_jsonable(memory)))
            else:
                row.user_id = str(memory.user_id)
                row.is_deleted = memory.is_deleted
                row.is_archived = memory.is_archived
                row.payload = to_jsonable(memory)
        return memory.memory_id

    def get_episodic(self, memory_id: UUID) -> Optional[EpisodicMemory]:
        with session_scope(self._sf) as s:
            row = s.query(m.EpisodicMemory).filter_by(memory_id=str(memory_id)).one_or_none()
            return from_jsonable(EpisodicMemory, row.payload) if row else None

    def all_episodic(self, user_id) -> list[EpisodicMemory]:
        with session_scope(self._sf) as s:
            rows = s.query(m.EpisodicMemory).filter_by(user_id=str(user_id)).all()
            return [from_jsonable(EpisodicMemory, r.payload) for r in rows]

    def active_episodic(self, user_id) -> list[EpisodicMemory]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.EpisodicMemory)
                    .filter_by(user_id=str(user_id), is_deleted=False, is_archived=False).all())
            return [from_jsonable(EpisodicMemory, r.payload) for r in rows]

    # ── Semantic ─────────────────────────────────────────────────────────
    def save_semantic(self, memory: SemanticMemory) -> UUID:
        with session_scope(self._sf) as s:
            row = s.query(m.SemanticMemory).filter_by(memory_id=str(memory.memory_id)).one_or_none()
            if row is None:
                s.add(m.SemanticMemory(
                    user_id=str(memory.user_id), memory_id=str(memory.memory_id),
                    is_deprecated=memory.is_deprecated, payload=to_jsonable(memory)))
            else:
                row.user_id = str(memory.user_id)
                row.is_deprecated = memory.is_deprecated
                row.payload = to_jsonable(memory)
        return memory.memory_id

    def active_semantic(self, user_id) -> list[SemanticMemory]:
        with session_scope(self._sf) as s:
            rows = (s.query(m.SemanticMemory)
                    .filter_by(user_id=str(user_id), is_deprecated=False).all())
            return [from_jsonable(SemanticMemory, r.payload) for r in rows]

    # ── Identity (cross-user) ────────────────────────────────────────────
    def save_identity(self, belief: IdentityMemory) -> UUID:
        with session_scope(self._sf) as s:
            row = s.query(m.IdentityMemory).filter_by(belief_id=str(belief.belief_id)).one_or_none()
            if row is None:
                s.add(m.IdentityMemory(
                    belief_id=str(belief.belief_id), is_immutable=belief.is_immutable,
                    payload=to_jsonable(belief)))
            else:
                row.is_immutable = belief.is_immutable
                row.payload = to_jsonable(belief)
        return belief.belief_id

    def identity_beliefs(self) -> list[IdentityMemory]:
        with session_scope(self._sf) as s:
            rows = s.query(m.IdentityMemory).all()
            return [from_jsonable(IdentityMemory, r.payload) for r in rows]

    # ── Recall candidates ────────────────────────────────────────────────
    def candidate_memories(self, user_id) -> list[Memory]:
        return [*self.active_episodic(user_id), *self.active_semantic(user_id)]

    # ── User World Model ─────────────────────────────────────────────────
    def save_uwm(self, uwm: UserWorldModel) -> None:
        with session_scope(self._sf) as s:
            row = s.query(m.UserWorldModel).filter_by(user_id=str(uwm.user_id)).one_or_none()
            if row is None:
                s.add(m.UserWorldModel(user_id=str(uwm.user_id), payload=to_jsonable(uwm)))
            else:
                row.payload = to_jsonable(uwm)

    def load_uwm(self, user_id) -> Optional[UserWorldModel]:
        with session_scope(self._sf) as s:
            row = s.query(m.UserWorldModel).filter_by(user_id=str(user_id)).one_or_none()
            return from_jsonable(UserWorldModel, row.payload) if row else None

    def query_uwm(self, user_id, query_type: str, context: str = "") -> dict:
        return resolve_uwm_query(self.load_uwm(user_id), query_type, context)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_postgres_memory_store.py -q`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/layer2_memory/memory_store.py backend/layer2_memory/__init__.py \
        infra/db/memory_store.py tests/unit/infra/test_postgres_memory_store.py
git commit -m "feat(infra): PostgresMemoryStore drop-in for Layer-2 store interface

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Store↔arbiter integration (fidelity linchpin)

**Files:**
- Test: `tests/unit/infra/test_store_arbiter_integration.py`

**Interfaces:**
- Consumes: `PostgresMemoryStore` (Task 3); real `memory_arbiter` + `DeterministicEmbedder` from `backend.layer2_memory`.

This task adds no source — it proves the store is a faithful drop-in by running the **real** arbiter against it (mirrors the API increment's `test_assembly_turn`). It is its own task because it verifies a different property (whole-arbiter recall) than Task 3's method-level tests.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/test_store_arbiter_integration.py
import asyncio
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone

from backend.layer2_memory import memory_arbiter, DeterministicEmbedder
from backend.layer2_memory.schemas import ConversationMode, EmotionVector, EpisodicMemory
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore


def _store():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresMemoryStore(make_session_factory(engine))


def test_arbiter_recalls_a_persisted_memory():
    emb = DeterministicEmbedder()
    store = _store()
    text = "user loves hiking in the mountains every weekend"
    store.save_episodic(EpisodicMemory(
        user_id="u1", summary=text, embedding=emb.embed(text),
        created_at=datetime.now(timezone.utc), S_current=1.0, importance_score=0.6))
    packet = asyncio.run(memory_arbiter(
        "u1", "tell me about hiking", EmotionVector(), ConversationMode.CASUAL,
        datetime.now(timezone.utc), store=store, embedder=emb))
    assert packet.recalled_memories
    assert not packet.confabulation_guard


def test_arbiter_empty_store_sets_confabulation_guard():
    packet = asyncio.run(memory_arbiter(
        "u1", "hi", EmotionVector(), ConversationMode.CASUAL, datetime.now(timezone.utc),
        store=_store(), embedder=DeterministicEmbedder()))
    assert packet.confabulation_guard
    assert packet.cold_start
```

- [ ] **Step 2: Run test to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_store_arbiter_integration.py -q`
Expected: PASS (2 passed).
If `test_arbiter_recalls_a_persisted_memory` fails with an empty `recalled_memories`, the context gate zeroed the candidate for `CASUAL` — debug via `context_gate.gate_value(ConversationMode.CASUAL, context_gate.memory_gate_kind(mem))`; do NOT weaken the assertion.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/infra/test_store_arbiter_integration.py
git commit -m "test(infra): real memory_arbiter recalls from PostgresMemoryStore

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Wire the store + real episodic write into build_app_state

**Files:**
- Modify: `api/state.py` (swap store; replace writer)
- Test: `tests/unit/api/test_state.py` (rewrite writer test; add restart-simulation test)

**Interfaces:**
- Consumes: `PostgresMemoryStore` (Task 3); `EpisodicMemory` dataclass; existing `build_pipeline_steps`.
- Produces: `make_episodic_writer(store, embed_client, session_factory) -> Callable` (replaces `make_session_writer`). `build_app_state` now constructs `PostgresMemoryStore(session_factory)` and passes it as both the recall store and the writer's store.

- [ ] **Step 1: Write the failing test**

Replace `tests/unit/api/test_state.py` with:

```python
import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from datetime import datetime, timezone

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from api.state import build_app_state, make_episodic_writer


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
    return build_app_state(config={"system": {"default_user_id": "local-user"}, "llm": {}},
                           llm_clients=clients, engine=engine, vector_store=object())


class Ctx:
    user_id = "local-user"
    session_id = "s1"
    message = "hey there"
    now = datetime.now(timezone.utc)


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_episodic_writer_persists_memory_and_session():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    make_episodic_writer(store, FakeLLM(), factory)(Ctx())
    assert len(store.active_episodic("local-user")) == 1
    with session_scope(factory) as s:
        assert s.query(models.Session).filter_by(session_key="s1").one().turn_count == 1


def test_persisted_memory_survives_store_rebuild():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    make_episodic_writer(PostgresMemoryStore(factory), FakeLLM(), factory)(Ctx())
    # Fresh store object over the same database — simulates a process restart.
    rebuilt = PostgresMemoryStore(factory)
    recalled = rebuilt.active_episodic("local-user")
    assert len(recalled) == 1 and recalled[0].summary == "hey there"
    assert recalled[0].embedding == [0.1, 0.2, 0.3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/api/test_state.py -q`
Expected: FAIL — `ImportError: cannot import name 'make_episodic_writer'`.

- [ ] **Step 3: Write minimal implementation**

In `api/state.py`: update imports, replace `make_session_writer` with `make_episodic_writer`, and update `build_app_state` to use `PostgresMemoryStore`.

Change the import block near the top:

```python
from datetime import datetime, timezone

from config import load_config
from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from backend.layer2_memory.schemas import EpisodicMemory
from backend.pipeline import ConversationOrchestrator
from api.assembly import build_pipeline_steps
```

(Remove the now-unused `from backend.layer2_memory import InMemoryMemoryStore` import.)

Replace the whole `make_session_writer` function with:

```python
def make_episodic_writer(store, embed_client, session_factory) -> Callable:
    """Post-turn writer: upsert the Session turn count and persist a real EpisodicMemory.

    The turn message is embedded (via the injected embed client) and saved through the store,
    so recall reads it back on later turns and after a restart. LLM-summarization extraction is
    a later increment — `summary` is the raw message for now. Best-effort and swallowed: the
    response is already delivered, so post-turn bookkeeping must never surface to the user.
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
            message = getattr(ctx, "message", "") or ""
            episode = EpisodicMemory(
                user_id=ctx.user_id,
                summary=message[:2000],
                embedding=embed_client.embed([message])[0] if message else [],
                created_at=getattr(ctx, "now", None) or datetime.now(timezone.utc),
                importance_score=0.3,
                S_current=1.0,
                creation_agent="api.episodic_writer")
            store.save_episodic(episode)
        except Exception:
            logger.exception("episodic writer failed; turn already delivered")
    return _write
```

In `build_app_state`, replace the `steps = build_pipeline_steps(...)` block:

```python
    store = PostgresMemoryStore(session_factory)
    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=store,
        session_writer=make_episodic_writer(store, llm_clients["embed"], session_factory))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/api/test_state.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add api/state.py tests/unit/api/test_state.py
git commit -m "feat(api): persist recall to Postgres via PostgresMemoryStore + real episodic write

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Docker integration test (live Postgres JSONB)

**Files:**
- Create: `tests/integration_infra/test_memory_store_postgres.py`

**Interfaces:**
- Consumes: `PostgresMemoryStore`; the `postgres_url` fixture in `tests/integration_infra/conftest.py`.

- [ ] **Step 1: Confirm the fixture name**

Run: `grep -n "def postgres_url\|def postgres" tests/integration_infra/conftest.py`
Expected: a fixture that yields a Postgres URL and skips when the container is unreachable. Use its exact name in Step 2 (below assumes `postgres_url`).

- [ ] **Step 2: Write the test**

```python
# tests/integration_infra/test_memory_store_postgres.py
import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory.schemas import EpisodicMemory, UserWorldModel, PersonNode
from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.memory_store import PostgresMemoryStore

pytestmark = pytest.mark.docker


def test_episodic_roundtrip_against_live_postgres(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    store = PostgresMemoryStore(make_session_factory(engine))
    uid = f"itest-{uuid4()}"
    text = "persisted through real JSONB"
    store.save_episodic(EpisodicMemory(
        user_id=uid, summary=text, embedding=[0.1, 0.2, 0.3],
        created_at=datetime.now(timezone.utc), S_current=0.9))
    got = store.active_episodic(uid)
    assert len(got) == 1 and got[0].summary == text and got[0].S_current == 0.9


def test_uwm_roundtrip_against_live_postgres(postgres_url):
    engine = make_engine(postgres_url)
    init_db(engine)
    store = PostgresMemoryStore(make_session_factory(engine))
    uid = uuid4()
    uwm = UserWorldModel(user_id=uid)
    uwm.relationship_graph.people.append(PersonNode(name="Alex"))
    store.save_uwm(uwm)
    loaded = store.load_uwm(str(uid))
    assert loaded.relationship_graph.people[0].name == "Alex"
```

- [ ] **Step 3: Run against the live stack (informational — skips offline)**

Run: `docker compose -f docker/docker-compose.yml up -d postgres && /usr/bin/python3.11 -m pytest tests/integration_infra/test_memory_store_postgres.py -q -m docker`
Expected: PASS if `psycopg`/`sqlalchemy` are installed and Postgres is up; otherwise auto-skips. (If deps aren't on the system interpreter, run in the project venv.)

- [ ] **Step 4: Commit**

```bash
git add tests/integration_infra/test_memory_store_postgres.py
git commit -m "test(infra): docker memory-store roundtrip against live Postgres JSONB

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Docs reconciliation + full-suite gate

**Files:**
- Modify: `CLAUDE.md` (API Layer section: persistence boundary now includes real episodic persistence)
- Modify: `docs/superpowers/specs/2026-07-05-postgres-memory-store-design.md` (Status → Implemented)

- [ ] **Step 1: Update CLAUDE.md**

In the "### API Layer (`api/`)" section, update the persistence description: the live `/chat` recall path now reads from `PostgresMemoryStore` (not `InMemoryMemoryStore`), and the post-turn writer persists a real `EpisodicMemory` (JSONB payload + embedding) that survives restarts. Move "Layer-2-store↔ORM bridge" out of the "Not yet wired" list; keep **Chroma ANN live-path**, **per-user Layer 4/5/7/11/13 state**, and **reinforcement/UWM/audit write-back** in the deferred list (they are increments #2/#3).

- [ ] **Step 2: Update the spec status line**

Change the spec header `**Status:**` from `Approved (design), pending implementation plan` to `Implemented`.

- [ ] **Step 3: Full offline suite gate**

Run: `/usr/bin/python3.11 -m pytest tests/ -q`
Expected: all prior tests still pass **plus** the new ones; new skips only where `@pytest.mark.docker`/`importorskip` apply. Confirm the count increased and nothing regressed.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-07-05-postgres-memory-store-design.md
git commit -m "docs: reconcile CLAUDE.md + spec status for PostgresMemoryStore

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes (author)

- **Spec coverage:** §4.1 store interface → Task 3; §4.2 models + UWM table → Task 2; §4.3 serde round-trip → Task 1; §4.4 read-path wiring → Task 5; §4.5 write-path wiring → Task 5; §6 error handling → arbiter fallback exercised in Task 4, writer swallow in Task 5; §7 testing → Tasks 1–6; §8 success criteria 1–4 → Tasks 5 (write+recall), 5/6 (restart), 3 (interface), 3+existing (no consumer changes).
- **Deviation from spec §4.2:** the `IdentityMemory` promoted `key` column and the `EpisodicMemory` business-time `created_at` column are dropped as YAGNI — the identity dataclass has no `key` field, and nothing queries by business time this increment (recall reads `created_at` from the reconstructed payload; the mixin's row-time `created_at` remains). Filtering columns are exactly what the read path uses: `is_deleted`/`is_archived`/`is_deprecated`/`user_id`.
- **Layer-2 edit:** Task 3 Step 1a extracts `resolve_uwm_query` from `InMemoryMemoryStore` and delegates — behavior-preserving, guarded by Step 1b against existing tests. This is the single intentional Layer-2 change; consumers (arbiter/recall/state_updater) are untouched.
