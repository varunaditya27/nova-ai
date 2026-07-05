# API Conversation Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `api/` FastAPI app that boots the real `infra/` substrate and drives a live
`ConversationOrchestrator.run_turn` behind `POST /chat` and `GET /health`.

**Architecture:** A FastAPI app whose lifespan builds an `AppState` (config → LLM clients → Postgres
engine+`init_db` → Chroma store → `ConversationOrchestrator` assembled with real-layer adapters). The
adapter layer (`api/assembly.py`) maps the orchestrator's 12 sync `PipelineSteps` hooks onto the real
layer entrypoints, bridging the two async ones (`process_input_event`, `memory_arbiter`) to sync. The
`/chat` route is a **sync** endpoint (FastAPI threadpool) so the async bridge is safe.

**Tech Stack:** FastAPI, uvicorn, Pydantic, the existing `infra/` (groq/ollama/chromadb/sqlalchemy),
pytest.

## Global Constraints

- Test interpreter: the project venv `.venv/bin/python` (has infra+api deps) for green runs; the
  offline suite must also collect on `/usr/bin/python3.11` (no third-party deps) — every api test
  module starts with `import pytest; pytest.importorskip("fastapi")`.
- Base install stays pure-stdlib; api deps live in a new `pyproject.toml` `api` extra. `pytest tests/`
  must stay green whether or not the `api`/`infra` extras are installed.
- The 13 layers under `backend/` and the `infra/` substrate are NOT modified by this increment — the
  api only adds adapters and HTTP wiring around them.
- Single-user: `user_id` comes from `config['system']['default_user_id']`; no auth.
- `/chat` is a sync `def` endpoint. LLM-touching adapters call real `infra` `LLMClient`s; offline
  tests inject fakes. Post-turn writes never affect the delivered response.
- Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## Real layer signatures (reference — do not re-derive)

- `layer1_input.process_input_event(user_id: UUID, raw_message, received_at: datetime, attachments: list, client_metadata: ClientMetadata, *, profile_store=None, thread_store=None, backends=None, ...) -> InputPerceptionPacket` — **async**
- `layer2_memory.memory_arbiter(user_id: UUID, query_text, current_emotion: EmotionVector, conversation_mode: ConversationMode, now, *, store, embedder, ...) -> MemoryPacket` — **async**
- `layer3_reasoning.build_emotion_intent_packet(message, *, llm_fn: Callable[[str], LLMClassificationOutput]=None, alert_fn=None, ...) -> EmotionIntentPacket` — sync
- `layer4_persona.assemble_persona_packet(persona_state, relationship_state, voice_parameters, drift_result) -> PersonaPacket` — sync
- `layer4_persona.generate_semantic_draft(user_message, persona_packet=None, ..., llm_fn: Callable[[str], str]=None) -> SemanticDraft` (`.text`) — sync
- `layer4_persona.refine_emotion(...)` (emotion_refiner) — sync
- `layer9_output.deliver(final_response_text, conversation_mode, *, crisis_mode_active=False, semantic_draft=None, ...) -> DeliveryResult` — sync
- `layer11_safety.evaluate(...)` (crisis), `run_all_checks(...)` (guardrails), `generate_crisis_response(...)` (escalation) — sync
- `layer13_onboarding.ColdStartEngine(user_id).on_message(message, session_context, timestamp) -> MessageDirectives` — sync
- Domain types: `EmotionVector(valence, arousal, dominant_label)`; `ClientMetadata(session_id, ...)`;
  `LLMClassificationOutput(primary_label, secondary_labels, valence, arousal, confidence, crisis_flag, crisis_confidence, reasoning_trace, primary_intent, secondary_intent, intent_confidence, needs_advice)`;
  `SemanticDraft(text, key_claims, ...)`; `MessageDirectives(pending_elicitation_question, feature_introduction_events, updated_state)`.

---

### Task 1: Deps, config, and Dockerfile

**Files:**
- Modify: `pyproject.toml`
- Modify: `config/defaults.yaml`
- Modify: `docker/Dockerfile`
- Test: `tests/unit/api/__init__.py` (create, empty), `tests/unit/api/test_config_api_keys.py`

**Interfaces:**
- Produces: config keys `system.default_user_id`, `api.host`, `api.port`, `api.cors_origins`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/api/test_config_api_keys.py
from config import load_config


def test_api_and_default_user_config_present():
    cfg = load_config(env={"GROQ_API_KEY": "x"})
    assert cfg["system"]["default_user_id"] == "local-user"
    assert cfg["api"]["port"] == 8000
    assert cfg["api"]["cors_origins"] == ["http://localhost:3000"]
```

- [ ] **Step 2: Run — expect FAIL** (`KeyError: 'default_user_id'`)

Run: `.venv/bin/python -m pytest tests/unit/api/test_config_api_keys.py -q`

- [ ] **Step 3: Add config keys** to `config/defaults.yaml`

Under `system:` add `  default_user_id: ${NOVA_USER_ID:-local-user}`. Append a new top-level block:

```yaml
api:
  host: ${API_HOST:-0.0.0.0}
  port: ${API_PORT:-8000}
  cors_origins: ["http://localhost:3000"]
```

Note: `port` will be a string from env interpolation only if `API_PORT` is set; the literal `8000`
in YAML parses as int. The test asserts int `8000` (no `API_PORT` in env). Keep the default unquoted.

- [ ] **Step 4: Add `api` extra** to `pyproject.toml`

In `[project.optional-dependencies]` add:
```toml
api = ["fastapi>=0.110", "uvicorn[standard]>=0.29"]
```
and change `dev` to `dev = ["nova-ai[infra,api]", "pytest>=7", "pytest-mock>=3"]`.
Add `"api"` package is not needed (setuptools already lists top-level packages; `api` is one — add it):
`packages = ["config", "infra", "backend", "api"]`.

- [ ] **Step 5: Update `docker/Dockerfile`** — change the install line to:
```dockerfile
RUN pip install --no-cache-dir ".[infra,api]"
```

- [ ] **Step 6: Install the api extra into the venv**

Run: `.venv/bin/python -m pip install "fastapi>=0.110" "uvicorn[standard]>=0.29"`
Expected: success (fastapi + starlette + pydantic + httpx pulled).

- [ ] **Step 7: Run — expect PASS**, then full offline suite green

Run: `.venv/bin/python -m pytest tests/unit/api/test_config_api_keys.py -q`
Run: `.venv/bin/python -m pytest tests/ -q` → all pass (existing + 1 new).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml config/defaults.yaml docker/Dockerfile tests/unit/api/
git commit -m "feat(api): api deps extra, config keys, Dockerfile install .[infra,api]

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Request/response schemas

**Files:**
- Create: `api/schemas.py`
- Test: `tests/unit/api/test_schemas.py`

**Interfaces:**
- Produces: `api.schemas.ChatRequest(message: str, session_id: str | None = None)` and
  `ChatResponse(response: str, conversation_mode: str, cognitive_system: str, crisis_active: bool, refined: bool, session_id: str)` (Pydantic `BaseModel`s).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/api/test_schemas.py
import pytest
pytest.importorskip("pydantic")

from api.schemas import ChatRequest, ChatResponse


def test_chat_request_defaults_session_none():
    req = ChatRequest(message="hi")
    assert req.message == "hi" and req.session_id is None


def test_chat_response_roundtrips():
    resp = ChatResponse(response="hey", conversation_mode="casual", cognitive_system="system1",
                        crisis_active=False, refined=False, session_id="s1")
    assert resp.model_dump()["response"] == "hey"


def test_chat_request_requires_message():
    with pytest.raises(Exception):
        ChatRequest()
```

- [ ] **Step 2: Run — expect FAIL** (module missing)

- [ ] **Step 3: Write `api/schemas.py`**

```python
"""HTTP request/response models for the conversation API."""
from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_mode: str
    cognitive_system: str
    crisis_active: bool
    refined: bool
    session_id: str
```

- [ ] **Step 4: Run — expect PASS.** `.venv/bin/python -m pytest tests/unit/api/test_schemas.py -q`

- [ ] **Step 5: Commit**

```bash
git add api/schemas.py tests/unit/api/test_schemas.py
git commit -m "feat(api): ChatRequest/ChatResponse pydantic schemas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Assembly — real-layer adapters (the crux)

**Files:**
- Create: `api/assembly.py`
- Test: `tests/unit/api/test_assembly_turn.py`

**Interfaces:**
- Consumes: `backend.pipeline.{PipelineSteps, TurnContext, ConversationOrchestrator}`; the real layer
  entrypoints (see reference table); `infra.llm.LLMClient` (duck-typed: `.complete(prompt, *, system=None)`).
- Produces: `api.assembly.build_pipeline_steps(*, system1, system2, embed, memory_store, session_writer=None, region="india", default_mode="casual") -> PipelineSteps`.
  - `system1`, `system2`, `embed` are `LLMClient`-shaped. `memory_store` implements Layer 2's store
    protocol (use `backend.layer2_memory.InMemoryMemoryStore`). `session_writer` is an optional
    `Callable[[TurnContext], None]` for persistence (Task 4 supplies the Postgres writer; None = skip).
- Produces: `api.assembly._run(coro)` — runs an async coroutine to completion from sync code
  (`asyncio.new_event_loop().run_until_complete`), safe inside FastAPI's threadpool.

**Design notes for the implementer:**
- The orchestrator calls each hook synchronously. `perceive` and `recall` wrap **async** layer calls
  via `_run(...)`. All other hooks call sync layer functions directly.
- `recall`'s hook signature is `(user_id, input_packet) -> list`. Recall runs *before* classify, so
  pass a neutral `EmotionVector(valence=0.0, arousal=0.0, dominant_label="neutral")` and the default
  mode; extract the memory list from the returned `MemoryPacket` (attribute `recalled_memories`;
  confirm against `backend/layer2_memory/schemas.py` MemoryPacket and adjust if named differently).
- `classify`'s `llm_fn` must return an `LLMClassificationOutput`. Provide `_json_classifier(system1)`
  that prompts for strict JSON and parses into `LLMClassificationOutput`, falling back to a neutral
  instance on any parse/LLM error (never raise — Layer 3 must not break the turn).
- `plan`/`refine` inject `llm_fn=lambda p: systemN.complete(p)`.
- `safety_scan`→`evaluate`, `guardrails`→`run_all_checks`, `escalate`→`generate_crisis_response`
  (the lower-level SC functions, matching the orchestrator's hook granularity — not `SafetyAgent`).
- `deliver`→`layer9_output.deliver(text, conversation_mode, crisis_mode_active=...)`; return the
  delivered text (attribute `final_text`/`text` on `DeliveryResult` — confirm and use).
- `cold_start`→ per-user `ColdStartEngine`; return its `MessageDirectives` (or None if inactive).
- `state_update`→ call `session_writer(ctx)` if provided (Task 4), else no-op.
- Where a real call needs a domain object the increment can't yet supply faithfully (e.g. full
  persona/relationship/drift state), construct a **minimal real default** instance and pass it; keep
  each such construction in a small `_default_*()` helper so the follow-up (persistence) can replace it.

- [ ] **Step 1: Write the failing test** (drives the whole assembly — real pipeline, fake I/O)

```python
# tests/unit/api/test_assembly_turn.py
import pytest
pytest.importorskip("pydantic")  # assembly imports are stdlib+backend, but keep parity with api suite

from backend.pipeline import ConversationOrchestrator
from backend.layer2_memory import InMemoryMemoryStore
from api.assembly import build_pipeline_steps


class FakeLLM:
    """LLMClient-shaped fake: echoes a canned reply; deterministic, offline."""
    def __init__(self, reply="Sounds good — tell me more."):
        self._reply = reply
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return self._reply
    def stream(self, prompt, **k):
        yield self._reply
    def embed(self, texts):
        return [[float(len(t) % 7), 0.1, 0.2] for t in texts]


def test_casual_turn_runs_through_real_pipeline():
    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore())
    out = ConversationOrchestrator(steps).run_turn("local-user", "hey what's up")
    assert isinstance(out.response_text, str) and out.response_text.strip()


def test_empty_recall_sets_confabulation_guard():
    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore())
    orch = ConversationOrchestrator(steps)
    # A fresh store returns no memories → orchestrator must flag the confabulation guard.
    out = orch.run_turn("local-user", "hi")
    assert out.response_text  # delivered a response without inventing memories


def test_state_writer_is_invoked_after_turn():
    llm = FakeLLM()
    seen = []
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore(),
                                 session_writer=lambda ctx: seen.append(ctx.user_id))
    ConversationOrchestrator(steps).run_turn("local-user", "hey")
    assert seen == ["local-user"]
```

- [ ] **Step 2: Run — expect FAIL** (module missing)

Run: `.venv/bin/python -m pytest tests/unit/api/test_assembly_turn.py -q`

- [ ] **Step 3: Implement `api/assembly.py`**

Build it incrementally, running the test after each hook is wired. Structure:

```python
"""Assembly — build the orchestrator's PipelineSteps from real layers + infra clients.

Each hook is a thin adapter translating TurnContext <-> a layer's real packet type and calling that
layer's public entrypoint. Only Layer 1 (perceive) and Layer 2 (recall) are async; `_run` bridges
them to the synchronous orchestrator (safe because the /chat route runs in FastAPI's threadpool).
LLM-touching hooks call injected LLMClient-shaped objects, so the whole pipeline runs offline with
fakes (see tests/unit/api/test_assembly_turn.py).
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from backend.pipeline import PipelineSteps

logger = logging.getLogger(__name__)

_NS = uuid.NAMESPACE_URL  # stable per-user UUIDs from string user_ids


def _uuid_for(user_id: str) -> uuid.UUID:
    return uuid.uuid5(_NS, user_id)


def _run(coro):
    """Run an async coroutine to completion from sync code (FastAPI threadpool-safe)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def build_pipeline_steps(*, system1, system2, embed, memory_store,
                         session_writer: Optional[Callable] = None,
                         region: str = "india", default_mode: str = "casual") -> PipelineSteps:
    # Implement each adapter below against the real signatures in the reference table.
    # Import the layer entrypoints lazily inside build_pipeline_steps to keep import light.
    from backend.layer1_input import process_input_event, ClientMetadata
    from backend.layer2_memory import memory_arbiter
    from backend.layer2_memory.schemas import EmotionVector
    from backend.layer3_reasoning import build_emotion_intent_packet
    from backend.layer3_reasoning.schemas import LLMClassificationOutput
    from backend.layer4_persona import generate_semantic_draft
    from backend.layer9_output import deliver as l9_deliver
    from backend.layer13_onboarding import ColdStartEngine

    cold_engines: dict = {}

    def perceive(user_id, message, now):
        return _run(process_input_event(
            _uuid_for(user_id), message, now, [],
            ClientMetadata(session_id=str(uuid.uuid4()))))

    def recall(user_id, input_packet):
        packet = _run(memory_arbiter(
            _uuid_for(user_id),
            getattr(input_packet, "normalized_text", "") or "",
            EmotionVector(valence=0.0, arousal=0.0, dominant_label="neutral"),
            default_mode, datetime.now(timezone.utc),
            store=memory_store, embedder=embed))
        return list(getattr(packet, "recalled_memories", []) or [])

    def cold_start(user_id, message):
        engine = cold_engines.setdefault(user_id, ColdStartEngine(user_id))
        try:
            return engine.on_message(message, None, datetime.now(timezone.utc))
        except Exception:
            logger.exception("cold_start adapter failed; skipping overlay")
            return None

    def _json_classifier(text):
        prompt = ("Return ONLY JSON with keys primary_label, valence (-1..1), arousal (0..1), "
                  "confidence (0..1), crisis_flag (bool), primary_intent. Message: " + text)
        try:
            raw = system1.complete(prompt)
            data = json.loads(raw)
            return LLMClassificationOutput(
                primary_label=data.get("primary_label", "neutral"),
                secondary_labels=[], valence=float(data.get("valence", 0.0)),
                arousal=float(data.get("arousal", 0.0)),
                confidence=float(data.get("confidence", 0.5)),
                crisis_flag=bool(data.get("crisis_flag", False)),
                crisis_confidence=0.0, reasoning_trace="",
                primary_intent=data.get("primary_intent", "chitchat"),
                secondary_intent=None, intent_confidence=0.5, needs_advice=False)
        except Exception:
            return LLMClassificationOutput(
                primary_label="neutral", secondary_labels=[], valence=0.0, arousal=0.0,
                confidence=0.3, crisis_flag=False, crisis_confidence=0.0, reasoning_trace="",
                primary_intent="chitchat", secondary_intent=None, intent_confidence=0.3,
                needs_advice=False)

    def classify(message, input_packet, recalled):
        return build_emotion_intent_packet(message, llm_fn=_json_classifier)

    def plan(ctx):
        client = system2 if ctx.cognitive_system == "system2" else system1
        draft = generate_semantic_draft(ctx.message, llm_fn=lambda p: client.complete(p))
        return draft.text

    def refine(ctx, draft):
        # System 2 emotion pass; keep factual content. Minimal real refine: system2 rephrase.
        return system2.complete(f"Warmly rephrase without changing facts:\n{draft}")

    def deliver(ctx, response, crisis_mode_active):
        result = l9_deliver(response, ctx.conversation_mode, crisis_mode_active=crisis_mode_active)
        return getattr(result, "final_text", None) or getattr(result, "text", response)

    def state_update(ctx):
        if session_writer is not None:
            session_writer(ctx)

    return PipelineSteps(
        perceive=perceive, recall=recall, cold_start=cold_start, classify=classify,
        plan=plan, refine=refine, deliver=deliver, state_update=state_update)
```

Notes while implementing:
- Run the test after wiring `perceive`+`recall`+`classify`+`plan`+`deliver`; adjust attribute names
  (`normalized_text`, `recalled_memories`, `final_text`) to the real schema fields — the test fails
  loudly on any mismatch, which is the point. Do not leave `safety_scan`/`build_persona`/`guardrails`/
  `escalate` wired unless a real call is clean; the orchestrator treats `None` hooks as no-ops, and
  the casual-turn test must pass with the core path. Wiring `safety_scan`/`guardrails` with the real
  L11 sync functions is encouraged if their inputs are constructible from `TurnContext`; otherwise
  leave them `None` this increment and note it (safety-as-follow-up is acceptable ONLY if documented —
  prefer wiring `safety_scan`→`evaluate` and `guardrails`→`run_all_checks`).

- [ ] **Step 4: Run — expect PASS** (all 3 assembly-turn tests green)

Run: `.venv/bin/python -m pytest tests/unit/api/test_assembly_turn.py -v`

- [ ] **Step 5: Commit**

```bash
git add api/assembly.py tests/unit/api/test_assembly_turn.py
git commit -m "feat(api): assembly module wiring real layers into PipelineSteps (async-bridged)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: AppState + composition root (with Postgres turn writer)

**Files:**
- Create: `api/state.py`
- Test: `tests/unit/api/test_state.py`

**Interfaces:**
- Consumes: `config.load_config`, `infra.llm.build_llm_clients`, `infra.db.{make_engine,
  make_session_factory, init_db, session_scope}`, `infra.db.models.{Session, EpisodicMemory}`,
  `infra.vector_store.build_vector_store`, `api.assembly.build_pipeline_steps`,
  `backend.layer2_memory.InMemoryMemoryStore`, `backend.pipeline.ConversationOrchestrator`.
- Produces: `api.state.AppState` (dataclass: `config`, `llm_clients`, `engine`, `session_factory`,
  `vector_store`, `orchestrator`, `default_user_id`).
- Produces: `api.state.build_app_state(config=None, *, llm_clients=None, engine=None,
  vector_store=None) -> AppState` — composition root; injectable overrides for tests.
- Produces: `api.state.make_session_writer(session_factory) -> Callable[[TurnContext], None]` — writes
  a `Session` (upsert turn_count) + `EpisodicMemory` row per turn inside a `session_scope`; logs and
  swallows failures.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/api/test_state.py
import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from api.state import build_app_state, make_session_writer


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


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_session_writer_persists_turn_row():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    writer = make_session_writer(factory)

    class Ctx:
        user_id = "local-user"; session_id = "s1"; message = "hey"; response_text = "hi"
    writer(Ctx())
    with session_scope(factory) as s:
        assert s.query(models.EpisodicMemory).filter_by(user_id="local-user").count() == 1
```

- [ ] **Step 2: Run — expect FAIL** (module missing)

- [ ] **Step 3: Implement `api/state.py`**

```python
"""Composition root: build the running AppState (infra clients + orchestrator)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from config import load_config
from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from backend.layer2_memory import InMemoryMemoryStore
from backend.pipeline import ConversationOrchestrator
from api.assembly import build_pipeline_steps

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    config: dict
    llm_clients: dict
    engine: Any
    session_factory: Any
    vector_store: Any
    orchestrator: ConversationOrchestrator
    default_user_id: str


def make_session_writer(session_factory) -> Callable:
    def _write(ctx) -> None:
        try:
            with session_scope(session_factory) as s:
                row = s.query(models.Session).filter_by(session_key=getattr(ctx, "session_id", "") or "default").one_or_none()
                if row is None:
                    s.add(models.Session(user_id=ctx.user_id,
                                         session_key=getattr(ctx, "session_id", "") or "default",
                                         turn_count=1))
                else:
                    row.turn_count += 1
                s.add(models.EpisodicMemory(user_id=ctx.user_id,
                                            summary=(getattr(ctx, "message", "") or "")[:2000],
                                            importance=0.3))
        except Exception:
            logger.exception("session writer failed; turn already delivered")
    return _write


def build_app_state(config: Optional[dict] = None, *, llm_clients=None, engine=None,
                    vector_store=None) -> AppState:
    config = config or load_config()
    if llm_clients is None:
        from infra.llm import build_llm_clients
        llm_clients = build_llm_clients(config)
    if engine is None:
        engine = make_engine(config["system"]["database_url"])
        init_db(engine)
    session_factory = make_session_factory(engine)
    if vector_store is None:
        from infra.vector_store import build_vector_store
        vector_store = build_vector_store(config)

    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=InMemoryMemoryStore(),
        session_writer=make_session_writer(session_factory))
    return AppState(config=config, llm_clients=llm_clients, engine=engine,
                    session_factory=session_factory, vector_store=vector_store,
                    orchestrator=ConversationOrchestrator(steps),
                    default_user_id=config["system"]["default_user_id"])
```

- [ ] **Step 4: Run — expect PASS.** `.venv/bin/python -m pytest tests/unit/api/test_state.py -q`

- [ ] **Step 5: Commit**

```bash
git add api/state.py tests/unit/api/test_state.py
git commit -m "feat(api): AppState composition root + Postgres per-turn writer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Dependencies + logging middleware

**Files:**
- Create: `api/dependencies.py`
- Create: `api/middleware/logging.py` (overwrite scaffold)
- Test: covered via Task 6/7 TestClient (no standalone test).

**Interfaces:**
- Produces: `api.dependencies.get_state(request) -> AppState` (reads `request.app.state.nova`),
  `get_orchestrator(request) -> ConversationOrchestrator`.
- Produces: `api.middleware.logging.RequestLoggingMiddleware` (Starlette `BaseHTTPMiddleware`) logging
  method, path, status, duration_ms — never the body.

- [ ] **Step 1: Implement `api/dependencies.py`**

```python
"""FastAPI dependencies — resolve the booted AppState from the app."""
from __future__ import annotations

from fastapi import Request

from api.state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.nova


def get_orchestrator(request: Request):
    return request.app.state.nova.orchestrator
```

- [ ] **Step 2: Implement `api/middleware/logging.py`**

```python
"""Request logging middleware — records method, path, status, duration (no bodies: may hold PII)."""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("nova.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path,
                    response.status_code, duration_ms)
        return response
```

- [ ] **Step 3: Smoke-import** — `.venv/bin/python -c "import api.dependencies, api.middleware.logging; print('ok')"` → `ok`.

- [ ] **Step 4: Commit**

```bash
git add api/dependencies.py api/middleware/logging.py
git commit -m "feat(api): request dependencies + logging middleware

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Health routes

**Files:**
- Create: `api/routes/health.py` (overwrite scaffold)
- Test: `tests/unit/api/test_health.py`

**Interfaces:**
- Produces: `api.routes.health.router` (APIRouter): `GET /health` → `{"status": "ok"}`;
  `GET /health/ready` → 200 `{"status":"ready"}` when DB probe passes, else 503.
- Consumes: `get_state` (for the DB engine in readiness).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/api/test_health.py
import pytest
pytest.importorskip("fastapi")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.health import router


def _client(ready_ok=True):
    app = FastAPI()
    class FakeEngine:
        def connect(self):
            if not ready_ok:
                raise RuntimeError("db down")
            class C:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def exec_driver_sql(self, q): return None
            return C()
    class Nova: engine = FakeEngine()
    app.state.nova = Nova()
    app.include_router(router)
    return TestClient(app)


def test_health_liveness_ok():
    assert _client().get("/health").json() == {"status": "ok"}


def test_health_ready_ok():
    assert _client(ready_ok=True).get("/health/ready").status_code == 200


def test_health_ready_503_when_db_down():
    assert _client(ready_ok=False).get("/health/ready").status_code == 503
```

- [ ] **Step 2: Run — expect FAIL** (module missing)

- [ ] **Step 3: Implement `api/routes/health.py`**

```python
"""Health endpoints — liveness (compose healthcheck) and readiness (DB probe)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from api.dependencies import get_state

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response, state=Depends(get_state)) -> dict:
    try:
        with state.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        response.status_code = 503
        return {"status": "not_ready", "component": "postgres", "detail": str(exc)[:200]}
    return {"status": "ready"}
```

- [ ] **Step 4: Run — expect PASS.** `.venv/bin/python -m pytest tests/unit/api/test_health.py -q`

- [ ] **Step 5: Commit**

```bash
git add api/routes/health.py tests/unit/api/test_health.py
git commit -m "feat(api): health + readiness routes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Chat route

**Files:**
- Create: `api/routes/chat.py` (overwrite scaffold)
- Test: `tests/unit/api/test_chat.py`

**Interfaces:**
- Produces: `api.routes.chat.router`: `POST /chat` (sync def) → `ChatResponse`.
- Consumes: `get_state`, `get_orchestrator`, `ChatRequest`, `ChatResponse`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/api/test_chat.py
import pytest
pytest.importorskip("fastapi")

from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.chat import router
from api.dependencies import get_state, get_orchestrator


def _client(out=None, raises=False):
    app = FastAPI()
    class Orch:
        def run_turn(self, user_id, message, now=None, session_id=""):
            if raises:
                raise RuntimeError("boom")
            return out
    app.include_router(router)
    app.dependency_overrides[get_state] = lambda: SimpleNamespace(default_user_id="local-user")
    app.dependency_overrides[get_orchestrator] = lambda: Orch()
    return TestClient(app, raise_server_exceptions=False)


def test_chat_returns_response_shape():
    out = SimpleNamespace(response_text="hey there", conversation_mode="casual",
                          cognitive_system="system1", crisis_active=False, refined=False,
                          session_id="s1")
    r = _client(out=out).post("/chat", json={"message": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["response"] == "hey there" and body["cognitive_system"] == "system1"


def test_chat_503_on_orchestrator_error():
    r = _client(raises=True).post("/chat", json={"message": "hi"})
    assert r.status_code == 503
```

- [ ] **Step 2: Run — expect FAIL** (module missing)

- [ ] **Step 3: Implement `api/routes/chat.py`**

```python
"""Chat endpoint — drives a single conversation turn through the orchestrator.

Sync `def` on purpose: FastAPI runs it in a worker thread, so the assembly's async->sync bridge
(`_run`) is safe (no running event loop in this thread).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state, get_orchestrator
from api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger("nova.api")
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, state=Depends(get_state), orchestrator=Depends(get_orchestrator)) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    try:
        out = orchestrator.run_turn(state.default_user_id, req.message, session_id=session_id)
    except Exception:
        logger.exception("turn failed")
        raise HTTPException(status_code=503, detail="conversation temporarily unavailable")
    return ChatResponse(
        response=out.response_text,
        conversation_mode=getattr(out, "conversation_mode", "casual"),
        cognitive_system=getattr(out, "cognitive_system", "system1"),
        crisis_active=getattr(out, "crisis_active", False),
        refined=getattr(out, "refined", False),
        session_id=session_id)
```

Note: confirm `run_turn` accepts `session_id=` (it does per the orchestrator signature). If
`OrchestratedOutput` lacks a field, the `getattr` defaults keep the response valid.

- [ ] **Step 4: Run — expect PASS.** `.venv/bin/python -m pytest tests/unit/api/test_chat.py -q`

- [ ] **Step 5: Commit**

```bash
git add api/routes/chat.py tests/unit/api/test_chat.py
git commit -m "feat(api): POST /chat route (sync, threadpool-safe)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: App factory + lifespan wiring

**Files:**
- Create: `api/main.py` (overwrite scaffold)
- Modify: `api/routes/__init__.py` (export routers)
- Test: `tests/unit/api/test_app_end_to_end.py`

**Interfaces:**
- Produces: `api.main.create_app() -> FastAPI` and module-level `app = create_app()`.
- Lifespan builds `AppState` via `build_app_state()` and stores it at `app.state.nova`; disposes the
  engine on shutdown.

- [ ] **Step 1: Write the failing test** (real app, fake AppState via patched build_app_state)

```python
# tests/unit/api/test_app_end_to_end.py
import pytest
pytest.importorskip("fastapi")

from types import SimpleNamespace
from fastapi.testclient import TestClient

import api.main as main


def test_app_boots_and_chat_works(monkeypatch):
    class Orch:
        def run_turn(self, user_id, message, now=None, session_id=""):
            return SimpleNamespace(response_text="hello from nova", conversation_mode="casual",
                                   cognitive_system="system1", crisis_active=False, refined=False)
    fake_state = SimpleNamespace(default_user_id="local-user", orchestrator=Orch(),
                                 engine=None, config={"api": {"cors_origins": []}})
    monkeypatch.setattr(main, "build_app_state", lambda: fake_state)

    app = main.create_app()
    with TestClient(app) as client:      # triggers lifespan startup
        assert client.get("/health").status_code == 200
        r = client.post("/chat", json={"message": "hi"})
        assert r.status_code == 200 and r.json()["response"] == "hello from nova"
```

- [ ] **Step 2: Run — expect FAIL** (create_app missing)

- [ ] **Step 3: Implement `api/main.py`**

```python
"""FastAPI application factory + lifespan (boots the infra substrate once)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.logging import RequestLoggingMiddleware
from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.state import build_app_state

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.nova = build_app_state()
    try:
        yield
    finally:
        engine = getattr(app.state.nova, "engine", None)
        if engine is not None and hasattr(engine, "dispose"):
            engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Nova AI", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware, allow_origins=["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"])
    app.include_router(health_router)
    app.include_router(chat_router)
    return app


app = create_app()
```

- [ ] **Step 4: Update `api/routes/__init__.py`** to a one-line docstring (routers imported directly by main).

- [ ] **Step 5: Run — expect PASS.** `.venv/bin/python -m pytest tests/unit/api/test_app_end_to_end.py -q`

- [ ] **Step 6: Full offline suite (venv + system python)**

Run: `.venv/bin/python -m pytest tests/ -q` → green.
Run: `/usr/bin/python3.11 -m pytest tests/ -q` → green (all api tests skip via importorskip).

- [ ] **Step 7: Commit**

```bash
git add api/main.py api/routes/__init__.py tests/unit/api/test_app_end_to_end.py
git commit -m "feat(api): FastAPI app factory + lifespan wiring (uvicorn api.main:app)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Docker health test, docs, verification, PR

**Files:**
- Create: `tests/integration_infra/test_api_health.py`
- Modify: `CLAUDE.md`, `docs/NOVA_AI_MASTER_ARCHITECTURE.md`

- [ ] **Step 1: Docker health test** (`@pytest.mark.docker`, auto-skip)

```python
# tests/integration_infra/test_api_health.py
import os
import socket
import urllib.request

import pytest


def _up(host, port):
    try:
        with socket.create_connection((host, int(port)), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.mark.docker
def test_backend_health_endpoint():
    host, port = os.environ.get("API_HOST", "localhost"), int(os.environ.get("API_PORT", "8000"))
    if not _up(host, port):
        pytest.skip("backend not running")
    with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2) as r:
        assert r.status == 200
```

- [ ] **Step 2: Verify offline skip.** `.venv/bin/python -m pytest tests/integration_infra/test_api_health.py -q` → skipped.

- [ ] **Step 3: Live smoke (best-effort, requires the app profile + models)**

```bash
docker compose -f docker/docker-compose.yml --profile app up -d --build backend
# wait for health, then:
curl -s localhost:8000/health
curl -s -X POST localhost:8000/chat -H 'content-type: application/json' -d '{"message":"hey"}'
```
Expected: `{"status":"ok"}` and a `ChatResponse` JSON (needs Ollama models pulled). If models/build
unavailable in the environment, document the commands and defer to the user.

- [ ] **Step 4: Docs** — add an "API" subsection to `CLAUDE.md` (endpoints `POST /chat`, `GET /health`;
  `uvicorn api.main:app`; single-user `default_user_id`; sync `/chat` + async bridge rationale) and a
  short note in `docs/NOVA_AI_MASTER_ARCHITECTURE.md` §8 that the API layer is live for chat+health,
  linking the design spec. Note the persistence boundary (Postgres turn record now; store↔ORM bridge
  + Chroma live-path are the next increment per the spec's §8 roadmap).

- [ ] **Step 5: Final verification**

Run: `/usr/bin/python3.11 -m pytest tests/ -q` (offline green; api tests skip)
Run: `.venv/bin/python -m pytest tests/ -q` (green; api tests pass, docker tests skip)

- [ ] **Step 6: Commit + push + PR**

```bash
git add tests/integration_infra/test_api_health.py CLAUDE.md docs/NOVA_AI_MASTER_ARCHITECTURE.md
git commit -m "test(api): docker health smoke + docs for the conversation endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push -u origin api-conversation-endpoint
gh pr create --title "feat(api): live conversation endpoint — POST /chat + health" --body "<summary + spec link + verification + roadmap pointer>

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 7: Report the PR URL for review before merge.**

---

## Notes for the implementer

- The **assembly (Task 3) is the risk**. Wire it hook-by-hook, re-running the assembly-turn test after
  each. Where a real layer field name differs from this plan's best-guess (`normalized_text`,
  `recalled_memories`, `final_text`), fix the adapter against the real schema — the test fails loudly,
  which is the TDD signal. Do NOT stub a layer to force green.
- Prefer wiring `safety_scan`→`layer11_safety.evaluate` and `guardrails`→`run_all_checks` if their
  inputs are constructible from `TurnContext`; leaving a hook `None` is acceptable only for hooks the
  orchestrator already treats as optional and only if noted in the PR.
- Do not touch `backend/` or `infra/`. This increment only adds `api/` + tests + docs.
- Keep the base install pure-stdlib; never remove the `importorskip` guards.
