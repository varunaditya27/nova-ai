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
from infra.db.relationship_store import PostgresRelationshipStore
from infra.db.proactive_store import PostgresProactiveQueue
from backend.layer7_goals.schemas import GoalStatus
from api.assembly import build_pipeline_steps
from api.proactive_gen import goal_checkin_item
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
    tool_manager: Any = None
    voice_backend: Any = None


def build_voice_backend(config: dict):
    """Kokoro TTS backend (Layer-9) with a real httpx transport, or None if httpx is unavailable.
    Adapts an httpx response to the `.ok/.status_code/.content` shape the backend expects; any
    connection error degrades to a non-ok AudioResult inside the backend (voice falls back to text)."""
    from types import SimpleNamespace
    try:
        import httpx
    except Exception:
        logger.warning("httpx unavailable; voice synthesis disabled")
        return None
    from backend.layer9_output.tts_backends.kokoro_backend import KokoroBackend

    tts = config.get("tts", {}) or {}
    endpoint = tts.get("endpoint") or "http://localhost:8880"

    def _request(method, url, payload=None):
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload) if method == "POST" else client.get(url)
        return SimpleNamespace(ok=r.is_success, status_code=r.status_code, content=r.content)

    return KokoroBackend(endpoint=endpoint, default_voice=tts.get("default_voice", "af_sky"),
                         request_fn=_request)


def build_tool_manager(session_factory, user_id, intent_client=None):
    """A single Layer-8 ToolManager for the process: durable action audit + registered plugins
    (local/offline backends). Held on AppState so the /chat pipeline and /tools routes share it —
    pending confirmations issued in a turn are confirmable on a later request.

    When an ``intent_client`` (a fast small model, e.g. gemma2:2b) is supplied, tool turns route by
    keyword (conservative) but have their parameters filled by the model, so SOFT/HARD actions form
    a real confirmation instead of asking one clarification per turn. Without it, the deterministic
    keyword fallback is used (offline-safe).
    """
    from backend.layer8_tools import ToolManager
    from backend.layer8_tools.plugins.calendar_plugin import CalendarPlugin
    from backend.layer8_tools.plugins.email_plugin import EmailPlugin
    from backend.layer8_tools.plugins.notes_plugin import NotesPlugin
    from backend.layer8_tools.plugins.reminders_plugin import RemindersPlugin
    from backend.layer8_tools.plugins.web_search_plugin import WebSearchPlugin
    from infra.db.action_recorder import PostgresActionRecorder

    tm = ToolManager(recorder=PostgresActionRecorder(session_factory, user_id))
    for plugin in (RemindersPlugin(), NotesPlugin(), CalendarPlugin(),
                   EmailPlugin(), WebSearchPlugin()):
        tm.register_plugin(plugin)

    if intent_client is not None:
        from backend.layer8_tools.llm_intent import make_llm_intent_fn

        def _required_for(tool, operation):
            p = tm.get_plugin(tool)
            if p is None or not p.supports(operation):
                return []
            return list(getattr(p.capability_for(operation), "required_params", []) or [])

        tm._intent_fn = make_llm_intent_fn(lambda prompt: intent_client.complete(prompt),
                                           _required_for)
    return tm


def make_state_update_writer(store, embed_client, session_factory, threshold: float,
                             vector_store=None) -> Callable:
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
                ep = EpisodicMemory(
                    user_id=ctx.user_id, summary=message[:2000],
                    embedding=embed_client.embed([message])[0], created_at=now,
                    importance_score=0.3, S_current=1.0, creation_agent="api.state_update")
                if vector_store is not None:   # index for the ANN live recall path (best-effort)
                    try:
                        vector_store.add("episodic", ids=[str(ep.memory_id)],
                                         embeddings=[ep.embedding],
                                         metadatas=[{"user_id": str(ctx.user_id)}],
                                         documents=[message[:500]])
                    except Exception:
                        logger.exception("vector-store index failed; recall falls back to linear")
                return [ep]

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
        from infra.llm.json_extract import extract_json
        return extract_json(system1_client.complete(prompt))   # clean fenced/prose JSON for the extractor

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


@dataclass
class _ColdStartDirectives:
    """The subset of Layer-13 directives the orchestrator consumes during cold-start overlay."""
    proactivity_mode: str = "observe_only"
    personality_drift_gate: float = 0.30
    pending_elicitation: Any = None


def make_cold_start_provider(session_factory, graduation_sessions: int) -> Callable:
    """Layer-13 cold-start hook: persisted-state-driven overlay.

    Reads the per-user onboarding record and, while still cold-starting, returns observe-only /
    drift-gated directives; returns None once graduated so the overlay self-terminates (the
    graduation counter is advanced post-turn by make_onboarding_writer). The full elicitation /
    feature-pacing machinery needs a persisted session_context this increment does not build.
    """
    def _provider(user_id, message):
        try:
            state = PostgresOnboardingStore(session_factory, user_id, graduation_sessions).state()
        except Exception:
            logger.exception("cold-start state read failed; skipping overlay")
            return None
        return _ColdStartDirectives() if state.get("cold_start_active") else None
    return _provider


def make_goal_provider(session_factory, embed_client) -> Callable:
    """Layer-7 → Layer-4: return the titles of goals relevant to this turn, for accountability
    injection into the planner prompt (via response_instruction)."""
    def _sim(a, b):
        return cosine_similarity(embed_client.embed([a])[0], embed_client.embed([b])[0])

    def _provider(user_id, message):
        relevant = PostgresGoalStore(session_factory, user_id).get_relevant_goals(
            message or "", similarity_fn=_sim)
        return [rg.goal.title for rg in relevant if getattr(rg.goal, "title", None)]
    return _provider


def make_relationship_provider(session_factory) -> Callable:
    """Load the persisted per-user relationship state for the persona packet."""
    def _provider(user_id):
        return PostgresRelationshipStore(session_factory, user_id).load()
    return _provider


def make_relationship_writer(session_factory) -> Callable:
    """Post-turn: advance the per-user relationship (message/session counters + stage)."""
    def _write(ctx) -> None:
        try:
            PostgresRelationshipStore(session_factory, ctx.user_id).record_turn(
                getattr(ctx, "session_id", "") or "default")
        except Exception:
            logger.exception("relationship writer failed; turn already delivered")
    return _write


def make_proactive_writer(session_factory, graduation_sessions: int) -> Callable:
    """Post-turn: wire the Layer-6 candidate-generation into the turn — enqueue/refresh a grounded
    GOAL_CHECK_IN for each active goal with an upcoming deadline/milestone, so ``GET /proactive``
    accumulates real outreach candidates. Suppressed while cold-starting (Layer-13 keeps proactivity
    observe-only). Idempotent: items are upserted by a goal-derived id, so re-running never dupes."""
    _ACTIVE = [GoalStatus.ACTIVE.value, GoalStatus.ON_TRACK.value, GoalStatus.AT_RISK.value]

    def _write(ctx) -> None:
        try:
            uid = ctx.user_id
            if PostgresOnboardingStore(session_factory, uid, graduation_sessions) \
                    .state().get("cold_start_active"):
                return
            now = getattr(ctx, "now", None) or datetime.now(timezone.utc)
            goals = PostgresGoalStore(session_factory, uid).load_by_status(_ACTIVE)
            if not goals:
                return
            queue = PostgresProactiveQueue(session_factory, uid)
            for goal in goals:
                item = goal_checkin_item(goal, now)
                if item is not None:
                    queue.upsert(item)
        except Exception:
            logger.exception("proactive writer failed; turn already delivered")
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
    config = config or load_config("local.yaml")   # local.yaml overlay is optional (skipped if absent)
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
        make_state_update_writer(store, llm_clients["embed"], session_factory, threshold,
                                 vector_store=vector_store),
        make_goal_writer(session_factory, llm_clients["system1"], llm_clients["embed"]),
        make_safety_writer(session_factory),
        make_onboarding_writer(session_factory, grad_sessions),
        make_relationship_writer(session_factory),
        make_proactive_writer(session_factory, grad_sessions))
    default_user_id = config["system"]["default_user_id"]
    tool_manager = build_tool_manager(session_factory, default_user_id,
                                      intent_client=llm_clients.get("intent"))
    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=store, session_writer=session_writer,
        cold_start=make_cold_start_provider(session_factory, grad_sessions),
        tool_manager=tool_manager,
        goal_provider=make_goal_provider(session_factory, llm_clients["embed"]),
        relationship_provider=make_relationship_provider(session_factory),
        vector_store=vector_store)
    return AppState(
        config=config, llm_clients=llm_clients, engine=engine,
        session_factory=session_factory, vector_store=vector_store,
        orchestrator=ConversationOrchestrator(steps),
        default_user_id=default_user_id, tool_manager=tool_manager,
        voice_backend=build_voice_backend(config))
