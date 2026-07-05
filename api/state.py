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
from backend.layer2_memory.embedding import cosine_similarity
from backend.layer2_memory.schemas import EpisodicMemory, EmotionVector, ShortTermMemoryBuffer
from backend.layer7_goals import run_goal_pipeline
from backend.pipeline import ConversationOrchestrator
from infra.db.goal_store import PostgresGoalStore
from infra.db.safety_store import PostgresSafetyLog
from infra.db.onboarding_store import PostgresOnboardingStore
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


def make_safety_writer(session_factory) -> Callable:
    """Post-turn: append the turn's crisis assessment to the safety log (append-only; NONE skipped)."""
    def _write(ctx) -> None:
        try:
            assessment = getattr(ctx, "crisis_assessment", None)
            signal = getattr(assessment, "signal", None) if assessment is not None else None
            if signal is None or getattr(signal, "tier", "none") in ("none", "", None):
                return
            signal.user_id = signal.user_id or ctx.user_id
            signal.session_id = signal.session_id or getattr(ctx, "session_id", "") or ""
            PostgresSafetyLog(session_factory).record(signal)
        except Exception:
            logger.exception("safety writer failed; turn already delivered")
    return _write


def make_onboarding_writer(session_factory, graduation_sessions: int) -> Callable:
    """Post-turn: advance the per-user onboarding session counter (self-graduating)."""
    def _write(ctx) -> None:
        try:
            PostgresOnboardingStore(session_factory, ctx.user_id, graduation_sessions) \
                .record_turn(getattr(ctx, "session_id", "") or "default")
        except Exception:
            logger.exception("onboarding writer failed; turn already delivered")
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
    grad_sessions = config.get("onboarding", {}).get("graduation_sessions", 5)
    session_writer = _chain_writers(
        make_state_update_writer(store, llm_clients["embed"], session_factory, threshold),
        make_goal_writer(session_factory, llm_clients["system1"], llm_clients["embed"]),
        make_safety_writer(session_factory),
        make_onboarding_writer(session_factory, grad_sessions))
    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=store, session_writer=session_writer)
    return AppState(
        config=config, llm_clients=llm_clients, engine=engine,
        session_factory=session_factory, vector_store=vector_store,
        orchestrator=ConversationOrchestrator(steps),
        default_user_id=config["system"]["default_user_id"])
