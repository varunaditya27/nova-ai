"""Composition root: build the running AppState (infra clients + orchestrator).

`build_app_state` is the single place that constructs the concrete infra backends and assembles the
`ConversationOrchestrator`. Every external backend is override-injectable so tests build an AppState
against in-memory SQLite + fake LLM clients with no network.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

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


def make_state_update_writer(store, embed_client, session_factory, threshold: float) -> Callable:
    """Post-turn writer that runs the real Layer-2 state_updater against Postgres.

    Upserts the Session turn count, then extracts a new episode from the turn, reinforces the
    recalled memories the response actually reflected (similarity-gated), bumps the UWM version if
    present, and appends a persisted audit event for each — all durable across restarts. Best-effort
    and swallowed: the response is already delivered, so post-turn bookkeeping must never surface to
    the user (matches the orchestrator's state-update invariant).
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

    store = PostgresMemoryStore(session_factory)
    threshold = config.get("memory", {}).get("reinforcement_similarity_threshold", 0.5)
    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=store,
        session_writer=make_state_update_writer(store, llm_clients["embed"],
                                                session_factory, threshold))
    return AppState(
        config=config, llm_clients=llm_clients, engine=engine,
        session_factory=session_factory, vector_store=vector_store,
        orchestrator=ConversationOrchestrator(steps),
        default_user_id=config["system"]["default_user_id"])
