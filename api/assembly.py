"""Assembly — build the orchestrator's PipelineSteps from real layers + infra clients.

Each hook is a thin adapter translating TurnContext <-> a layer's real packet type and calling that
layer's public entrypoint. Only Layer 1 (perceive) and Layer 2 (recall) are async; ``_run`` bridges
them to the synchronous orchestrator (safe because the /chat route runs in FastAPI's threadpool, so
there is no already-running event loop in the calling thread). Every LLM-touching hook calls an
injected ``LLMClient``-shaped object, so the whole pipeline runs offline with fakes — see
``tests/unit/api/test_assembly_turn.py``.

Wired this increment: perceive, recall, classify, build_persona, plan, refine, deliver, state_update,
safety_scan (SC-2 crisis detection), escalate (SC-3 crisis response). Left as documented follow-ups
(both hooks are optional; the orchestrator treats them as no-ops when absent):
  - cold_start (Layer 13): a faithful session context depends on the onboarding-persistence layer
    (graduation state) — wiring a synthetic one would flag every turn cold-start-active.
  - guardrails (Layer 11 SC-1): `run_all_checks` returns an `EthicalGuardrailResult` whose shape
    (`passed`/`final_response`) needs adapting to the orchestrator's `approved`/`replacement`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
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


def build_pipeline_steps(*, system1, system2, embed, memory_store,
                         session_writer: Optional[Callable] = None,
                         region: str = "india", default_mode: str = "casual") -> PipelineSteps:
    from backend.layer1_input import process_input_event, ClientMetadata
    from backend.layer2_memory import memory_arbiter
    from backend.layer2_memory.schemas import ConversationMode, EmotionVector
    from backend.layer3_reasoning import build_emotion_intent_packet
    from backend.layer3_reasoning.schemas import LLMClassificationOutput
    from backend.layer4_persona import generate_semantic_draft
    from backend.layer4_persona.schemas import PersonaPacket
    from backend.layer9_output import deliver as l9_deliver
    from backend.layer11_safety import evaluate, generate_crisis_response
    from backend.layer11_safety.schemas import CrisisTier

    embedder = _EmbedderAdapter(embed)
    veto_tiers = {CrisisTier.TIER_1.value, CrisisTier.TIER_2.value}

    def perceive(user_id, message, now):
        packet = _run(process_input_event(
            _uuid_for(user_id), message, now, [],
            ClientMetadata(session_id=str(uuid.uuid4()))))
        setattr(packet, "raw_message", message)   # carry the text forward for recall
        return packet

    def recall(user_id, input_packet):
        packet = _run(memory_arbiter(
            _uuid_for(user_id), getattr(input_packet, "raw_message", "") or "",
            EmotionVector(valence=0.0, arousal=0.0, dominant_label="neutral"),
            ConversationMode.CASUAL, datetime.now(timezone.utc),
            store=memory_store, embedder=embedder))
        return list(getattr(packet, "recalled_memories", []) or [])

    def _json_classifier(text):
        prompt = ("Classify the message. Return ONLY JSON with keys primary_label (str), "
                  "valence (-1..1), arousal (0..1), confidence (0..1), crisis_flag (bool), "
                  "primary_intent (str). Message: " + text)
        try:
            data = json.loads(system1.complete(prompt))
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
        return build_emotion_intent_packet(message, llm_fn=_json_classifier)

    def safety_scan(user_id, message, input_packet):
        signal = evaluate(message)
        tier = getattr(signal, "tier", CrisisTier.NONE.value)
        return _CrisisAssessment(is_crisis=tier in veto_tiers, tier=tier, signal=signal)

    def build_persona(ctx):
        return PersonaPacket()

    def plan(ctx):
        client = system2 if ctx.cognitive_system == "system2" else system1
        draft = generate_semantic_draft(ctx.message, persona_packet=ctx.persona_packet,
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

    def deliver(ctx, response, crisis_mode_active):
        result = l9_deliver(response, ctx.conversation_mode, crisis_mode_active=crisis_mode_active)
        return getattr(result, "final_message_text", None) or response

    def state_update(ctx):
        if session_writer is not None:
            session_writer(ctx)

    return PipelineSteps(
        perceive=perceive, recall=recall, classify=classify,
        safety_scan=safety_scan, build_persona=build_persona, plan=plan, refine=refine,
        escalate=escalate, deliver=deliver, state_update=state_update)
