"""Composition root: build the running AppState (infra clients + orchestrator).

`build_app_state` is the single place that constructs the concrete infra backends and assembles the
`ConversationOrchestrator`. Every external backend is override-injectable so tests build an AppState
against in-memory SQLite + fake LLM clients with no network.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from config import load_config
from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail
from backend.layer2_memory import (
    state_updater, merge_uwm_update, apply_identity_update, detect_identity_contradictions,
    default_identity_beliefs,
)
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
    stm_store: Any = None


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


def _summarize_promoted_turn(client, turn) -> tuple[str, list[str]]:
    """LLM summary + named-entity extraction for one promoted STM turn, for its episodic-memory
    `summary`/`entity_refs` fields. `entity_refs` feeds §10.3's narrative-link `entity_overlap`
    term — without it, `link_score` can never exceed `0.6·semantic`, always under the `0.65`
    threshold, so two episodes about the same person/place/event could never actually link.
    Degrades to a plain truncation + no entities when no LLM client is available or the call
    fails (§15's best-effort rule) — matches the fallback shape of
    memory_consolidation_job.py's `_generalize`."""
    if client is None or not turn.content:
        return turn.content[:2000], []
    prompt = (
        "For this message from the user, produce a long-term memory record. Return ONLY JSON "
        "with two keys: \"summary\" (one or two sentences, third person, concise and factual, "
        "no commentary) and \"entities\" (a list of up to 5 short strings naming the specific "
        "people, places, or named things mentioned — e.g. a person's name, an employer, a city; "
        "omit generic nouns). Message:\n\n" + turn.content[:4000])
    try:
        from infra.llm.json_extract import extract_json
        data = json.loads(extract_json(client.complete(prompt)))
        summary = str(data.get("summary", "")).strip()[:2000] or turn.content[:2000]
        entities = [str(e).strip() for e in (data.get("entities") or []) if str(e).strip()][:5]
        return summary, entities
    except Exception:
        return turn.content[:2000], []


def _link_narrative_chains(store, user_id, new_episodes: list, now: datetime) -> None:
    """Attach each newly-promoted episode to an existing narrative arc, or seed a new one
    (§10.3). Best-effort: episodes are already saved, so a failure here must never lose them."""
    from backend.layer2_memory.audit_trail import detect_narrative_links
    from backend.layer2_memory.schemas import ChainedEpisode, NarrativeChain, NarrativeLinkType

    try:
        chains = store.active_narrative_chains(user_id)
        last_ids = {c.episodes[-1].episode_id for c in chains if c.episodes}
        episodes_by_id = {eid: ep for eid in last_ids
                          if (ep := store.get_episodic(eid)) is not None}
        for ep in new_episodes:
            chain = detect_narrative_links(ep, chains, episodes_by_id, now)
            if chain is None:
                chain = NarrativeChain(
                    theme=ep.summary[:80], first_episode_at=ep.created_at,
                    last_episode_at=ep.created_at,
                    episodes=[ChainedEpisode(episode_id=ep.memory_id, position_in_chain=0,
                                             link_type=NarrativeLinkType.CONTINUATION, linked_at=now)])
                chains.append(chain)
            store.save_narrative_chain(user_id, chain)
            episodes_by_id[ep.memory_id] = ep   # a second promoted episode this turn can chain onto it
    except Exception:
        logger.exception("narrative-chain linking failed; episodes already saved")


def _extract_uwm_signals(client, message: str) -> dict:
    """LLM extraction of User World Model signals from one message — profile facts, people
    mentioned, and active life situations/stressors (§7's schema, narrowed: communication_model
    is deliberately excluded here, see backend/layer2_memory/uwm_updater.py's docstring). Returns
    ``{}`` (a no-op for the merge step) when there's no client or the call/parse fails — matches
    the best-effort fallback shape used throughout this module (§15)."""
    if client is None or not message:
        return {}
    prompt = (
        "Read this message from a user talking to their AI companion. Return ONLY JSON with up "
        "to 4 keys, including only what this message actually states or clearly implies -- omit "
        "a key entirely if there's nothing to report, never guess or invent:\n"
        "\"profile\": object with any of preferred_name, pronouns, current_life_stage, "
        "field_of_study_or_work, institution_or_employer, career_goals_summary, "
        "likely_living_situation (strings) that this message reveals about the user themself;\n"
        "\"people\": list of {\"name\", \"relationship_tier\" (e.g. family/friend/partner/"
        "colleague), \"traits\": [short strings]} for specific people (not the user) named in "
        "this message;\n"
        "\"situations\": list of {\"description\", \"category\", \"emotional_weight\" (0-1)} for "
        "ongoing life situations mentioned (a project, a move, an illness, etc.);\n"
        "\"stressors\": list of {\"description\", \"category\", \"intensity\" (0-1)} for things "
        "causing the user stress right now.\n\nMessage:\n\n" + message[:4000])
    try:
        from infra.llm.json_extract import extract_json
        data = json.loads(extract_json(client.complete(prompt)))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def make_state_update_writer(store, embed_client, session_factory, threshold: float,
                             vector_store=None, stm_store=None, summarizer_llm=None) -> Callable:
    """Post-turn writer that runs the real Layer-2 state_updater against Postgres.

    Upserts the Session turn count, accumulates this turn into the session's real (in-process,
    RAM-only — see infra/stm_store.py) Short-Term Memory buffer, and — matching the architecture
    doc's actual design (§3.3), not a stand-in for it — creates an episodic memory only for turns
    that are *evicted from STM and pass promotion* (high emotional arousal or a life-event
    keyword), summarized by an LLM rather than raw-truncated. Also reinforces the recalled
    memories the response actually reflected (similarity-gated), bumps the UWM version if present,
    and appends a persisted audit event for each — all durable across restarts. Best-effort and
    swallowed: the response is already delivered, so post-turn bookkeeping must never surface to
    the user (matches the orchestrator's state-update invariant).
    """
    from backend.layer2_memory.stm import add_turn, should_promote
    from backend.layer2_memory.schemas import ConversationTurn

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

            emotion_intent = getattr(ctx, "emotion_intent", None)
            emotion = getattr(emotion_intent, "emotion_vector", None) or EmotionVector()

            # Accumulate into the real, cross-request STM buffer. Promotion is checked on
            # arrival, not on eviction: real sessions (a handful to a few dozen turns) will almost
            # never fill the 100-turn/30,000-char window, so eviction-only promotion would mean
            # significant turns are rarely, if ever, actually promoted. `should_promote` is a pure
            # function of a turn's own fields (which never mutate after construction), so checking
            # it again at eviction time for a turn that already failed the arrival check can only
            # ever repeat the same "no" — an eviction-time check adds no coverage, only a second
            # pass over turns already decided. Only user turns are eligible (Nova's own reply text
            # can accidentally contain a life-event keyword, e.g. "congratulations on the new job",
            # which is not something the *user* experienced).
            promotable = []
            if stm_store is not None:
                stm = stm_store.get_or_create(key, ctx.user_id)
                if message:
                    user_turn = ConversationTurn(
                        role="user", content=message, timestamp=now,
                        word_count=len(message.split()), emotional_annotation=emotion)
                    if should_promote(user_turn):
                        promotable.append(user_turn)
                    add_turn(stm, user_turn)
                if response:
                    assistant_turn = ConversationTurn(
                        role="assistant", content=response, timestamp=now,
                        word_count=len(response.split()))
                    add_turn(stm, assistant_turn)   # kept for in-session coherence
                stm_store.save(key, stm)
            else:
                stm = ShortTermMemoryBuffer(session_id=key, user_id=ctx.user_id)

            def _extractor(_stm, _emotion):
                episodes = []
                for turn in promotable:
                    summary, entities = _summarize_promoted_turn(summarizer_llm, turn)
                    ep = EpisodicMemory(
                        user_id=ctx.user_id, summary=summary, entity_refs=entities,
                        embedding=embed_client.embed([summary])[0], created_at=turn.timestamp or now,
                        importance_score=0.5, S_current=1.0, creation_agent="api.state_update",
                        emotion_vector=turn.emotional_annotation or EmotionVector())
                    if vector_store is not None:   # index for the ANN live recall path (best-effort)
                        try:
                            vector_store.add("episodic", ids=[str(ep.memory_id)],
                                             embeddings=[ep.embedding],
                                             metadatas=[{"user_id": str(ctx.user_id)}],
                                             documents=[summary[:500]])
                        except Exception:
                            logger.exception("vector-store index failed; recall falls back to linear")
                    episodes.append(ep)
                if episodes:
                    _link_narrative_chains(store, ctx.user_id, episodes, now)
                return episodes

            def _uwm_updater(existing_uwm):
                extracted = _extract_uwm_signals(summarizer_llm, message)
                return merge_uwm_update(existing_uwm, ctx.user_id, extracted, now)

            audit = PostgresAuditTrail(session_factory, ctx.user_id)
            state_updater(ctx.user_id, key, stm, store, audit, emotion, now, _extractor,
                          last_recall=recalled, used_memory_ids=used,
                          uwm_updater_fn=_uwm_updater)
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


def make_message_writer(session_factory) -> Callable:
    """Post-turn: persist both halves of the turn to the permanent conversation log (the transcript
    the /chat UI loads), attaching the recalled-memory echoes to Nova's message."""
    from infra.db.message_store import PostgresMessageStore

    def _write(ctx) -> None:
        try:
            store = PostgresMessageStore(session_factory, ctx.user_id)
            key = getattr(ctx, "session_id", "") or ""
            now = getattr(ctx, "now", None)
            user_msg = getattr(ctx, "message", "") or ""
            nova_msg = getattr(ctx, "delivered", None) or getattr(ctx, "response_text", "") or ""
            if user_msg:
                store.append("user", user_msg, session_key=key, created_at=now)
            if nova_msg:
                from api.echoes import project_echoes
                store.append(
                    "nova", nova_msg, session_key=key, created_at=now,
                    echoes=project_echoes(getattr(ctx, "recalled_memories", [])),
                    mode=getattr(ctx, "conversation_mode", None),
                    cognitive_system=getattr(ctx, "cognitive_system", None),
                    crisis_active=getattr(ctx, "crisis_active", False),
                    crisis_tier=str(getattr(ctx, "crisis_tier", "") or "") or None,
                    tool_invoked=getattr(ctx, "tool_invoked", False),
                    refined=getattr(ctx, "refined", False))
        except Exception:
            logger.exception("message writer failed; turn already delivered")
    return _write


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
    def _provider(user_id, message, session_id=""):
        try:
            store = PostgresOnboardingStore(session_factory, user_id, graduation_sessions)
            state = store.state()
        except Exception:
            logger.exception("cold-start state read failed; skipping overlay")
            return None
        if not state.get("cold_start_active"):
            return None
        directives = _ColdStartDirectives()
        # Active elicitation: pick at most one onboarding question to weave into this turn.
        try:
            from api.elicitation import select_elicitation
            el = store.elicitation_state(session_id)
            item = select_elicitation(message, state.get("session_index", 0) + 1,
                                      el["surfaced_targets"], el["asked_this_session"])
            if item is not None:
                directives.pending_elicitation = item
                store.record_elicitation(session_id, item.inference_target)   # never re-ask it
        except Exception:
            logger.exception("elicitation selection failed; overlay without a question")
        return directives
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


def make_uwm_provider(session_factory) -> Callable:
    """Load the persisted per-user User World Model for the persona packet (§7). Returns
    ``None`` until the first real signal is extracted (see uwm_updater_fn in
    make_state_update_writer) — the persona packet degrades to no UWM directive, matching every
    other provider's cold-start behavior."""
    store = PostgresMemoryStore(session_factory)

    def _provider(user_id):
        return store.load_uwm(user_id)
    return _provider


def make_identity_provider(session_factory) -> Callable:
    """Select a small, prompt-sized slice of Nova's self-model for the persona directive (§6) —
    the highest-centrality non-immutable beliefs, not the whole table. Identity Memory is Nova's
    own self-model, shared across the single user this app serves (IdentityMemory uses
    TimestampMixin, not UserScopedMixin) — the ``user_id`` param exists only so this provider has
    the same call shape as every other one (``provider(ctx.user_id)``)."""
    store = PostgresMemoryStore(session_factory)
    _TOP_N = 3

    def _provider(user_id=None):
        beliefs = [b for b in store.identity_beliefs() if not b.is_immutable]
        beliefs.sort(key=lambda b: b.centrality, reverse=True)
        return beliefs[:_TOP_N]
    return _provider


def _revise_belief_statement(client, belief, contradiction) -> str:
    """LLM rewrite of one identity belief's statement, given the evidence that contradicted it.
    Falls back to the belief's *unchanged* statement (never a placeholder like "[revised] X") on
    any failure — apply_identity_update treats an unchanged return as "couldn't rewrite this
    turn," not as a real update, so a failed call here correctly leaves the belief untouched
    rather than persisting garbage."""
    if client is None:
        return belief.statement
    prompt = (
        f"Nova (an AI companion) currently believes about herself: \"{belief.statement}\". "
        f"A conversation with the user gave this evidence against it: "
        f"\"{contradiction.evidence_summary}\". Write a revised version of the belief statement "
        f"that honestly incorporates this evidence -- one sentence, third person, starting with "
        f"\"Nova\", same style as the original. Return ONLY the revised sentence, no quotes, no "
        f"commentary.")
    try:
        revised = client.complete(prompt).strip().strip('"')
        return revised or belief.statement
    except Exception:
        return belief.statement


def make_identity_writer(session_factory, llm_client) -> Callable:
    """Post-turn: SC-4 contradiction detection + belief update (§6.4). One combined LLM call
    (backend/layer2_memory/identity.py::detect_identity_contradictions) checks the turn's message
    against every non-immutable belief; any belief it genuinely contradicts accumulates evidence
    toward its centrality-scaled threshold (§6.3) and is rewritten (by a second, real LLM call —
    see _revise_belief_statement) once crossed."""
    def _write(ctx) -> None:
        try:
            message = getattr(ctx, "message", "") or ""
            if not message:
                return
            store = PostgresMemoryStore(session_factory)
            beliefs = store.identity_beliefs()
            session_id = getattr(ctx, "session_id", "") or ""
            now = getattr(ctx, "now", None) or datetime.now(timezone.utc)
            contradictions = detect_identity_contradictions(llm_client, message, beliefs, session_id)
            if not contradictions:
                return
            by_id = {b.belief_id: b for b in beliefs}
            for contradiction in contradictions:
                belief = by_id.get(contradiction.belief_id)
                if belief is None:
                    continue
                apply_identity_update(
                    belief, contradiction, now=now,
                    generate_fn=lambda b, c: _revise_belief_statement(llm_client, b, c))
                store.save_identity(belief)
        except Exception:
            logger.exception("identity writer failed; turn already delivered")
    return _write


def make_temporal_profile_provider(session_factory, timezone_offset_hours: float = 0.0) -> Callable:
    """Layer 1 profile source: derive per-user temporal-history signals from state that is
    already persisted for Layer 4/5 (session counters) and the message log, instead of a
    dedicated Layer-1 store — see docs/layer-1-architecture.md §16 "Live wiring status". Without
    this, Layer 1 has no way to know a user's session history and every turn looks cold-start.

    ``timezone_offset_hours`` must match the same value threaded into ``UserTemporalProfile`` in
    ``api/assembly.py::perceive`` — the live circadian band is computed from local time, so the
    historical band histogram built here has to apply the identical offset or the two will
    silently diverge (see docs/layer-1-architecture.md §16, "Circadian histogram is UTC-based").

    Returns a plain dict (not a Layer-1 schema type — ``api/assembly.py`` owns building the
    ``UserTemporalProfile``/``UserBehaviorBaseline`` objects, matching ``make_goal_provider``
    returning titles rather than a Layer-4 packet).
    """
    from infra.db.message_store import PostgresMessageStore
    from backend.layer1_input.temporal_resolver import map_circadian_band

    def _as_utc(dt):
        if dt is None:
            return None
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

    def _provider(user_id) -> dict:
        rel = PostgresRelationshipStore(session_factory, user_id).load()
        msgs = PostgresMessageStore(session_factory, user_id)
        first = msgs.first()
        last_session_end = _as_utc(msgs.last_interaction_at())

        age_days = 0
        first_created_at = _as_utc(first["created_at"]) if first is not None else None
        if first_created_at is not None:
            age_days = max(0, (datetime.now(timezone.utc) - first_created_at).days)

        # Bounded recent sample (message_store.history caps at 200) — an approximation of recent
        # cadence/circadian pattern, not a precise lifetime histogram.
        recent = msgs.history(limit=200)
        recent_user = [r for r in recent if r.get("role") == "user"]

        # average_session_frequency_days is the mean GAP BETWEEN sessions, not age/total_sessions
        # (age/total_sessions is days-per-session averaged over the relationship's whole lifetime,
        # a different and mostly-smaller quantity — it silently defeats detect_temporal_anomaly's
        # gap-vs-cadence check by making the threshold far tighter than the user's actual cadence).
        # Derive it from each session's earliest message in the bounded window.
        session_starts: dict[str, datetime] = {}
        for r in recent:
            key = r.get("session_key") or ""
            ts = _as_utc(r["created_at"])
            if key not in session_starts or ts < session_starts[key]:
                session_starts[key] = ts
        ordered_starts = sorted(session_starts.values())
        if len(ordered_starts) >= 2:
            gaps_days = [(b - a).total_seconds() / 86400
                        for a, b in zip(ordered_starts, ordered_starts[1:])]
            avg_frequency = sum(gaps_days) / len(gaps_days)
        else:
            avg_frequency = 0.0

        band_counts: dict[str, int] = {}
        for r in recent_user:
            local_hour = (_as_utc(r["created_at"]) + timedelta(hours=timezone_offset_hours)).hour
            band = map_circadian_band(local_hour).value
            band_counts[band] = band_counts.get(band, 0) + 1
        total_banded = sum(band_counts.values())
        # Require a handful of samples before trusting the histogram — with too few, an unseen
        # band reading 0.0 would flag every message in that band as "atypical" (detect_temporal_
        # anomaly's own >= 5 total_sessions gate gets a user here quickly, but 5 sessions can still
        # mean very few *banded* user messages in a slow-cadence relationship).
        _MIN_BANDED_SAMPLES = 10
        typical_bands = ({b: c / total_banded for b, c in band_counts.items()}
                         if total_banded >= _MIN_BANDED_SAMPLES else {})

        lengths = sorted(len(r["content"]) for r in recent_user if r.get("content"))
        length_median = lengths[len(lengths) // 2] if lengths else None

        return {
            "total_sessions": rel.total_sessions,
            "relationship_age_days": age_days,
            "average_session_frequency_days": avg_frequency,
            "typical_bands": typical_bands,
            "last_session_end": last_session_end,
            "message_length_median_chars": length_median,
        }
    return _provider


def make_relationship_writer(session_factory) -> Callable:
    """Post-turn: advance the per-user relationship (message/session counters + stage)."""
    def _write(ctx) -> None:
        try:
            PostgresRelationshipStore(session_factory, ctx.user_id).record_turn(
                getattr(ctx, "session_id", "") or "default",
                user_message=getattr(ctx, "message", "") or "")
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
    # Each layerN.yaml overlay is optional (skipped if absent) and merges over defaults.yaml;
    # local.yaml applies last so it can override any of them for local/dev runs.
    _layer_files = [f"layer{n}.yaml" for n in range(1, 14)]
    config = config or load_config(*_layer_files, "local.yaml")
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
    # Idempotent: seeds Nova's self-model once, on whichever process first finds it empty — not
    # in a separate script a deployer has to remember to run, or identity_beliefs() stays []
    # forever and the persona directive wired below has nothing to read.
    if not store.identity_beliefs():
        for belief in default_identity_beliefs():
            store.save_identity(belief)
    threshold = config.get("memory", {}).get("reinforcement_similarity_threshold", 0.5)
    grad_sessions = config.get("onboarding", {}).get("graduation_sessions", 5)
    tz_offset = config.get("system", {}).get("timezone_offset_hours", 0.0)
    from infra.stm_store import InProcessSTMStore
    stm_store = InProcessSTMStore()
    session_writer = _chain_writers(
        make_message_writer(session_factory),
        make_state_update_writer(store, llm_clients["embed"], session_factory, threshold,
                                 vector_store=vector_store, stm_store=stm_store,
                                 summarizer_llm=llm_clients["system1"]),
        make_goal_writer(session_factory, llm_clients["system1"], llm_clients["embed"]),
        make_safety_writer(session_factory),
        make_onboarding_writer(session_factory, grad_sessions),
        make_relationship_writer(session_factory),
        make_proactive_writer(session_factory, grad_sessions),
        make_identity_writer(session_factory, llm_clients["system1"]))
    default_user_id = config["system"]["default_user_id"]
    tool_manager = build_tool_manager(session_factory, default_user_id,
                                      intent_client=llm_clients.get("intent"))
    from backend.layer1_input.config import Layer1Config
    steps = build_pipeline_steps(
        system1=llm_clients["system1"], system2=llm_clients["system2"],
        embed=llm_clients["embed"], memory_store=store, session_writer=session_writer,
        cold_start=make_cold_start_provider(session_factory, grad_sessions),
        tool_manager=tool_manager,
        goal_provider=make_goal_provider(session_factory, llm_clients["embed"]),
        relationship_provider=make_relationship_provider(session_factory),
        uwm_provider=make_uwm_provider(session_factory),
        identity_provider=make_identity_provider(session_factory),
        profile_provider=make_temporal_profile_provider(session_factory, tz_offset),
        vector_store=vector_store,
        layer1_config=Layer1Config.from_dict(config), timezone_offset_hours=tz_offset)
    return AppState(
        config=config, llm_clients=llm_clients, engine=engine,
        session_factory=session_factory, vector_store=vector_store,
        orchestrator=ConversationOrchestrator(steps),
        default_user_id=default_user_id, tool_manager=tool_manager,
        voice_backend=build_voice_backend(config), stm_store=stm_store)
