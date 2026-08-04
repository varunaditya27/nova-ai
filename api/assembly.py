"""Assembly — build the orchestrator's PipelineSteps from real layers + infra clients.

Each hook is a thin adapter translating TurnContext <-> a layer's real packet type and calling that
layer's public entrypoint. Only Layer 1 (perceive) and Layer 2 (recall) are async; ``_run`` bridges
them to the synchronous orchestrator (safe because the /chat route runs in FastAPI's threadpool, so
there is no already-running event loop in the calling thread). Every LLM-touching hook calls an
injected ``LLMClient``-shaped object, so the whole pipeline runs offline with fakes — see
``tests/unit/api/test_assembly_turn.py``.

All 13-layer hooks are now wired: perceive, recall, classify, cold_start (Layer 13), safety_scan
(SC-2), build_persona, plan, refine, guardrails (SC-1), escalate (SC-3), deliver, state_update.

  - guardrails (Layer 11 SC-1): built here — `run_all_checks` returns an `EthicalGuardrailResult`
    (`passed`/`final_response`); the adapter reports `approved=False` with the SC-1 `final_response`
    whenever SC-1 altered the text, so any block/modification is applied post-generation.
  - cold_start (Layer 13): injected by `api/state.py` (needs Postgres). It is persisted-state-driven
    — reads `PostgresOnboardingStore.state()` and overlays observe-only/gated directives while
    cold-starting, `None` once graduated. The full elicitation machinery (which needs a persisted
    session_context this increment does not build) is a documented follow-up.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Callable, Optional

from backend.pipeline import PipelineSteps

logger = logging.getLogger("nova.api")

_NS = uuid.NAMESPACE_URL  # stable per-user UUIDs derived from string user_ids
_CRISIS_TEXT = ("I'm really glad you told me. If you might be in danger right now, please contact your "
                "local emergency number or a crisis line — you deserve support from someone who can "
                "be right there with you.")


def _uuid_for(user_id: str) -> uuid.UUID:
    return uuid.uuid5(_NS, user_id)


def _run(coro):
    """Run an async coroutine to completion from sync code (FastAPI threadpool-safe)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _EmbedderAdapter:
    """Adapt an infra LLMClient (embed(list) -> list[list]) to Layer 2's Embedder (embed(str) -> list)."""

    def __init__(self, client):
        self._client = client

    def embed(self, text: str) -> list:
        return self._client.embed([text])[0]


@dataclass
class _CrisisAssessment:
    """Orchestrator-shaped view of an SC-2 CrisisSignal (exposes is_crisis + tier)."""
    is_crisis: bool
    tier: str
    signal: object = None


@dataclass
class _GuardrailResult:
    """Orchestrator-shaped view of an SC-1 EthicalGuardrailResult (approved/replacement/flags)."""
    approved: bool
    replacement: Optional[str]
    flags: list


@dataclass
class _ToolTurnOutcome:
    """Orchestrator-shaped view of a Layer-8 ToolUseOutput (handled + the response it owns)."""
    handled: bool
    response_text: str = ""


class _SingleProfileStore:
    """Wraps one pre-fetched ``UserTemporalProfile`` as a Layer-1 ``ProfileStore``.

    Layer 1's own store protocol is keyed by the uuid5 ``process_input_event`` derives from the
    raw user_id; the Postgres-backed lookup in ``profile_provider`` runs against the raw id
    upstream of that derivation (same reasoning as the ANN-recall raw-id note above), so this
    wrapper just ignores whatever key ``.get()`` is called with and returns the profile already
    resolved for this turn.
    """
    def __init__(self, profile) -> None:
        self._profile = profile

    def get(self, _user_id):
        return self._profile


def build_pipeline_steps(*, system1, system2, embed, memory_store,
                         session_writer: Optional[Callable] = None,
                         cold_start: Optional[Callable] = None,
                         tool_manager=None,
                         goal_provider: Optional[Callable] = None,
                         relationship_provider: Optional[Callable] = None,
                         profile_provider: Optional[Callable] = None,
                         vector_store=None,
                         region: str = "india", default_mode: str = "casual") -> PipelineSteps:
    from backend.layer1_input import process_input_event, ClientMetadata
    from backend.layer1_input.schemas import UserTemporalProfile, UserBehaviorBaseline
    from backend.layer2_memory import memory_arbiter
    from backend.layer2_memory.schemas import ConversationMode, EmotionVector
    from backend.layer3_reasoning import build_emotion_intent_packet
    from backend.layer3_reasoning.schemas import LLMClassificationOutput
    from backend.layer4_persona import generate_semantic_draft
    from backend.layer4_persona.schemas import PersonaPacket
    from backend.layer9_output import deliver as l9_deliver
    from backend.layer11_safety import evaluate, generate_crisis_response, run_all_checks
    from backend.layer11_safety.schemas import CrisisTier

    embedder = _EmbedderAdapter(embed)
    veto_tiers = {CrisisTier.TIER_1.value, CrisisTier.TIER_2.value}

    # Recall runs before Layer 3 classification by design (docs/NOVA_AI_MASTER_ARCHITECTURE.md §3
    # step 3 vs step 5), so recall_scorer's mood-congruent emotional_component has no Layer-3
    # EmotionClassification to use. Layer 1's composite_emotional_prior — a single [0,1]
    # pre-linguistic vulnerability signal — is the only "current emotion" proxy available this
    # early, so we map it onto valence/arousal rather than passing a hardcoded neutral vector
    # (which would make the β=0.30 component favor neutral-toned memories on every single turn,
    # backwards from the mood-congruent-recall design intent). Below the confidence floor, or
    # if Layer 1 didn't run, fall back to neutral rather than trusting a low-signal prior.
    _EMOTION_PRIOR_CONFIDENCE_FLOOR = 0.3

    def _emotion_from_input_packet(input_packet) -> EmotionVector:
        prior = getattr(input_packet, "composite_emotional_prior", None)
        confidence = getattr(input_packet, "prior_confidence", 0.0) or 0.0
        if prior is None or confidence < _EMOTION_PRIOR_CONFIDENCE_FLOOR:
            return EmotionVector(valence=0.0, arousal=0.0, dominant_label="neutral")
        prior = max(0.0, min(1.0, prior))
        return EmotionVector(valence=-prior, arousal=prior,
                             dominant_label="neutral" if prior < 0.3 else "vulnerable")

    def perceive(user_id, message, now, session_id=""):
        profile_store = None
        behavior_baseline = None
        if profile_provider is not None:
            try:
                d = profile_provider(user_id)
                profile_store = _SingleProfileStore(UserTemporalProfile(
                    user_id=_uuid_for(user_id),
                    total_sessions=d["total_sessions"],
                    relationship_age_days=d["relationship_age_days"],
                    average_session_frequency_days=d["average_session_frequency_days"],
                    typical_bands=d["typical_bands"],
                    last_session_end=d["last_session_end"]))
                behavior_baseline = UserBehaviorBaseline(
                    message_length_median_chars=d["message_length_median_chars"])
            except Exception:
                logger.exception("temporal profile provider failed; Layer 1 falls back to cold start")
        # NOTE: attachments are always [] and ClientMetadata carries no real behavioral timestamps
        # (latency/deletion/burst) — the client doesn't send them yet (ChatRequest has no fields
        # for them). SC-2's implicit-signal scoring and SC-3/SC-4 (multimodal/voice) are therefore
        # always neutral/inactive in the live pipeline; see docs/layer-1-architecture.md §16.
        packet = _run(process_input_event(
            _uuid_for(user_id), message, now, [],
            ClientMetadata(session_id=session_id or str(uuid.uuid4())),
            profile_store=profile_store, behavior_baseline=behavior_baseline))
        setattr(packet, "raw_message", message)   # carry the text forward for recall
        return packet

    def recall(user_id, input_packet):
        # NOTE: pass the RAW user_id (not a uuid5) so recall matches the write path + read routes,
        # which persist/read episodes under the raw user_id. With a vector store present, retrieve
        # candidates by ANN (nearest episodic neighbours) instead of a linear scan; degrades to the
        # linear path when the index is cold or the vector store is unavailable.
        query = getattr(input_packet, "raw_message", "") or ""
        recall_store = memory_store
        if vector_store is not None and query:
            try:
                from infra.db.ann_recall_store import AnnRecallStore
                recall_store = AnnRecallStore(memory_store, vector_store,
                                              embedder.embed(query), user_id)
            except Exception:
                logger.exception("ANN recall store setup failed; using base store")
                recall_store = memory_store
        packet = _run(memory_arbiter(
            user_id, query,
            _emotion_from_input_packet(input_packet),
            ConversationMode(default_mode), datetime.now(timezone.utc),
            store=recall_store, embedder=embedder))
        return list(getattr(packet, "recalled_memories", []) or [])

    def _json_classifier(text):
        prompt = ("Classify the message. Return ONLY JSON with keys primary_label (str), "
                  "valence (-1..1), arousal (0..1), confidence (0..1), crisis_flag (bool), "
                  "primary_intent (str). Message: " + text)
        try:
            from infra.llm.json_extract import extract_json
            data = json.loads(extract_json(system1.complete(prompt)))
            return LLMClassificationOutput(
                primary_label=str(data.get("primary_label", "neutral")),
                secondary_labels=[], valence=float(data.get("valence", 0.0)),
                arousal=float(data.get("arousal", 0.0)),
                confidence=float(data.get("confidence", 0.5)),
                crisis_flag=bool(data.get("crisis_flag", False)),
                crisis_confidence=0.0, reasoning_trace="",
                primary_intent=str(data.get("primary_intent", "chitchat")),
                secondary_intent=None, intent_confidence=0.5, needs_advice=False)
        except Exception:
            return LLMClassificationOutput(
                primary_label="neutral", secondary_labels=[], valence=0.0, arousal=0.0,
                confidence=0.3, crisis_flag=False, crisis_confidence=0.0, reasoning_trace="",
                primary_intent="chitchat", secondary_intent=None, intent_confidence=0.3,
                needs_advice=False)

    def classify(message, input_packet, recalled):
        # Forward the Layer 1 signals that are real in production (Phase 1/2 audits). NOT
        # implicit_intensity: Layer 1 pins it at exactly 0.10 live (no client behavioral data
        # yet), and the neutral-skip heuristic's gate is `< 0.1` — forwarding it would disable
        # that gate on every single turn. See docs/POLISH_BACKLOG.md.
        return build_emotion_intent_packet(
            message,
            circadian_band=getattr(input_packet, "circadian_band", "afternoon"),
            composite_prior=getattr(input_packet, "composite_emotional_prior", 0.0) or 0.0,
            prior_confidence=getattr(input_packet, "prior_confidence", 0.0) or 0.0,
            signal_mismatch_flag=getattr(input_packet, "signal_mismatch", False),
            llm_fn=_json_classifier)

    def safety_scan(user_id, message, input_packet):
        signal = evaluate(message)
        tier = getattr(signal, "tier", CrisisTier.NONE.value)
        return _CrisisAssessment(is_crisis=tier in veto_tiers, tier=tier, signal=signal)

    def build_persona(ctx):
        """Per-user Layer-4/5 persona packet: loads the persisted relationship state and turns the
        qualitative stage into a plain-language familiarity directive for the planner prompt."""
        packet = PersonaPacket()
        if relationship_provider is not None:
            try:
                rel = relationship_provider(ctx.user_id)
                if rel is not None:
                    packet.relationship_state = rel
                    stage = getattr(rel, "stage", "new")
                    msgs = getattr(rel, "total_messages_exchanged", 0)
                    sessions = getattr(rel, "total_sessions", 0)
                    packet.persona_instruction = (
                        f"You and the user are at the '{stage}' stage of a long-term relationship "
                        f"({msgs} messages across {sessions} sessions). Match that familiarity — "
                        f"warmer and more casual as it deepens; do not over-familiarize when new.")
                    # Fold in the per-user learned communication style (Layer 4/5 persona learning).
                    try:
                        from backend.layer4_persona.style_learning import persona_style_directive
                        style = persona_style_directive(rel)
                        if style:
                            packet.persona_instruction = f"{packet.persona_instruction} {style}"
                    except Exception:
                        logger.exception("style directive failed; persona without learned style")
            except Exception:
                logger.exception("relationship provider failed; using default persona")
        return packet

    def _goal_directive(ctx) -> str:
        if goal_provider is None:
            return ""
        try:
            titles = [t for t in (goal_provider(ctx.user_id, ctx.message) or []) if t]
        except Exception:
            logger.exception("goal provider failed; no accountability injection this turn")
            return ""
        if not titles:
            return ""
        joined = "; ".join(f"'{t}'" for t in titles[:3])
        return (f"The user has active goal(s): {joined}. If it fits naturally, reference their "
                f"progress or gently encourage them — never force it or lecture.")

    def _elicitation_directive(ctx) -> str:
        """Layer-13: weave a surfaced onboarding question in naturally (never front-loaded)."""
        item = getattr(ctx, "pending_elicitation", None)
        question = getattr(item, "question", None) if item is not None else None
        if not question:
            return ""
        return (f"Somewhere that feels natural in your reply — never as a form or an interrogation — "
                f"gently work in this question: \"{question}\". If it doesn't fit naturally, let it go.")

    def plan(ctx):
        client = system2 if ctx.cognitive_system == "system2" else system1
        directive = " ".join(d for d in (_goal_directive(ctx), _elicitation_directive(ctx)) if d)
        draft = generate_semantic_draft(ctx.message, persona_packet=ctx.persona_packet,
                                        response_instruction=directive,
                                        llm_fn=lambda p: client.complete(p))
        return draft.text

    def refine(ctx, draft):
        return system2.complete("Rephrase this warmly without changing any facts:\n\n" + draft)

    def escalate(ctx, assessment):
        try:
            resp = generate_crisis_response(
                getattr(assessment, "tier", CrisisTier.TIER_2.value),
                signal=getattr(assessment, "signal", None), region=region,
                llm_fn=lambda p: system2.complete(p))
            return (getattr(resp, "response_text", None) or getattr(resp, "message", None)
                    or _CRISIS_TEXT)
        except Exception:
            logger.exception("escalate adapter failed; using crisis fallback")
            return _CRISIS_TEXT

    def tool_use(ctx):
        """Layer 8: detect a tool intent and drive intent->clarify->confirm->execute for the turn.
        Returns a handled outcome (the response the tool turn owns) or None to fall through to
        normal generation. Only local/offline plugin backends — no third-party creds."""
        if tool_manager is None:
            return None
        out = tool_manager.process(ctx.message, user_id=ctx.user_id,
                                   session_id=getattr(ctx, "session_id", "") or None)
        if getattr(out, "clarification_question", None):
            return _ToolTurnOutcome(handled=True, response_text=out.clarification_question)
        req = getattr(out, "confirmation_request", None)
        if req is not None:
            desc = getattr(req, "action_description", "that")
            return _ToolTurnOutcome(handled=True, response_text=(
                f"I can {desc}. Want me to go ahead? (confirmation id: {req.request_id})"))
        if getattr(out, "tool_invoked", False) and getattr(out, "result", None) is not None:
            summary = getattr(out.result, "result_summary", "") or "Done."
            return _ToolTurnOutcome(handled=True, response_text=summary)
        return None

    def guardrails(ctx, response):
        """SC-1 post-generation ethical guardrails. Maps EthicalGuardrailResult -> the
        orchestrator's {approved, replacement, flags}: any SC-1 alteration (hard block or moderate
        modification) is applied by reporting approved=False with the SC-1 final_response."""
        gctx = SimpleNamespace(session_id=getattr(ctx, "session_id", "") or None,
                               has_real_deadline=False, vulnerability_score=0.0)
        result = run_all_checks(response, gctx)
        final = getattr(result, "final_response", None) or response
        changed = final != response
        return _GuardrailResult(
            approved=not changed, replacement=final,
            flags=[v.check_name for v in getattr(result, "violations", []) or []])

    def deliver(ctx, response, crisis_mode_active):
        result = l9_deliver(response, ctx.conversation_mode, crisis_mode_active=crisis_mode_active)
        return getattr(result, "final_message_text", None) or response

    def state_update(ctx):
        if session_writer is not None:
            session_writer(ctx)

    return PipelineSteps(
        perceive=perceive, recall=recall, classify=classify, cold_start=cold_start,
        safety_scan=safety_scan, build_persona=build_persona, tool_use=tool_use,
        plan=plan, refine=refine, guardrails=guardrails, escalate=escalate,
        deliver=deliver, state_update=state_update)
