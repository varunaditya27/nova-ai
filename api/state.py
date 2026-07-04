"""Composition root: build the running AppState (infra clients + orchestrator).

`build_app_state` is the single place that constructs the concrete infra backends and assembles the
`ConversationOrchestrator`. Every external backend is override-injectable so tests build an AppState
against in-memory SQLite + fake LLM clients with no network.
"""
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

logger = logging.getLogger("nova.api")


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
    """Return a post-turn writer that persists a Session (upsert turn_count) + EpisodicMemory row.

    Failures are logged and swallowed — the response is already delivered, so post-turn bookkeeping
    must never surface to the user (matches the orchestrator's state-update invariant).
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
                s.add(models.EpisodicMemory(
                    user_id=ctx.user_id,
                    summary=(getattr(ctx, "message", "") or "")[:2000], importance=0.3))
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
    return AppState(
        config=config, llm_clients=llm_clients, engine=engine,
        session_factory=session_factory, vector_store=vector_store,
        orchestrator=ConversationOrchestrator(steps),
        default_user_id=config["system"]["default_user_id"])
