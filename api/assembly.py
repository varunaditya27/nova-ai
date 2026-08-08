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

# Layer 4's RelationshipState.stage vocabulary (new/acquaintance/developing/established/close)
# differs from Layer 9's doc vocabulary (stranger/acquaintance/friend/close_friend) -- confirmed
# by grepping every literal Layer 9 branches on (format_adapter/thinking_pause/length_calibrator/
# micro_interaction_engine all use the doc's four stages). Forwarding Layer 4's stage unmapped
# would silently mis-register brand-new users as "close_friend"-adjacent (falls through to the
# `else` branch -> intimate register, contractions, fragments) -- the opposite of the doc's intent.
_LAYER9_STAGE_MAP = {
    "new": "stranger", "acquaintance": "acquaintance",
    "developing": "friend", "established": "friend", "close": "close_friend",
}

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
                         uwm_provider: Optional[Callable] = None,
                         identity_provider: Optional[Callable] = None,
                         social_provider: Optional[Callable] = None,
                         social_surface_writer: Optional[Callable] = None,
                         proactive_coaching_writer: Optional[Callable] = None,
                         profile_provider: Optional[Callable] = None,
                         vector_store=None,
                         layer1_config=None, timezone_offset_hours: float = 0.0,
                         region: str = "india", default_mode: str = "casual") -> PipelineSteps:
    from backend.layer1_input import process_input_event, ClientMetadata
    from backend.layer1_input.config import Layer1Config
    from backend.layer1_input.schemas import UserTemporalProfile, UserBehaviorBaseline

    l1_config = layer1_config or Layer1Config()
    from backend.layer2_memory import memory_arbiter
    from backend.layer2_memory.schemas import ConversationMode, EmotionVector
    from backend.layer3_reasoning import build_emotion_intent_packet
    from backend.layer3_reasoning.schemas import LLMClassificationOutput, BackgroundEmotionalState
    from backend.layer4_persona import (
        generate_semantic_draft, resolve_persona_state, calibrate_voice, detect_drift,
        refine_emotion, should_skip_refinement, compute_relationship_state,
    )
    from backend.layer4_persona.schemas import PersonaPacket, SemanticDraft, FinalResponsePacket
    from backend.layer5_relationship import build_social_intelligence_packet
    from backend.layer5_relationship.schemas import SocialGraph
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
        # Cold-start fallback still carries the configured timezone offset — it's a deployment
        # property, not something that depends on having session history (see
        # test_perceive_applies_configured_timezone_offset_to_circadian_band).
        profile_store = _SingleProfileStore(
            UserTemporalProfile(user_id=_uuid_for(user_id),
                                timezone_offset_hours=timezone_offset_hours))
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
                    last_session_end=d["last_session_end"],
                    timezone_offset_hours=timezone_offset_hours))
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
            profile_store=profile_store, behavior_baseline=behavior_baseline,
            config=l1_config))
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

    def classify(user_id, message, input_packet, recalled):
        # Forward the Layer 1 signals that are real in production (Phase 1/2 audits). NOT
        # implicit_intensity: Layer 1 pins it at exactly 0.10 live (no client behavioral data
        # yet), and the neutral-skip heuristic's gate is `< 0.1` — forwarding it would disable
        # that gate on every single turn. See docs/POLISH_BACKLOG.md.
        #
        # BES inputs (§4): now real, since Layer 2's UWM/episodic-memory work landed.
        # episodic_memories drives the 14-day valence trend; active_stressors comes straight off
        # the UWM's life_context (same Stressor schema compute_stressor_load expects — no
        # translation needed). psychological_model is NOT forwarded: the UWM narrow-slice scope
        # decision excluded it (still unextracted, would only ever be None).
        episodic_memories = []
        active_stressors = []
        try:
            episodic_memories = memory_store.active_episodic(user_id)
        except Exception:
            logger.exception("BES episodic lookup failed; classifying without valence trend")
        if uwm_provider is not None:
            try:
                uwm = uwm_provider(user_id)
                if uwm is not None:
                    active_stressors = uwm.life_context.active_stressors
            except Exception:
                logger.exception("BES stressor lookup failed; classifying without stressor load")
        return build_emotion_intent_packet(
            message,
            circadian_band=getattr(input_packet, "circadian_band", "afternoon"),
            composite_prior=getattr(input_packet, "composite_emotional_prior", 0.0) or 0.0,
            prior_confidence=getattr(input_packet, "prior_confidence", 0.0) or 0.0,
            signal_mismatch_flag=getattr(input_packet, "signal_mismatch", False),
            episodic_memories=episodic_memories,
            active_stressors=active_stressors,
            # Explicit tz-aware `now`: compute_background_state's own default is naive
            # (`datetime.utcnow()`), but real EpisodicMemory.created_at is stamped tz-aware
            # (see make_state_update_writer) -- without this, comparing the two inside
            # `_recent()` raises on every turn once real episodic data exists, and the BES
            # silently degrades to insufficient_data (caught via
            # test_real_layer3_wiring_forwards_episodic_memories_to_background_state).
            now=datetime.now(timezone.utc),
            llm_fn=_json_classifier)

    def safety_scan(user_id, message, input_packet):
        signal = evaluate(message)
        tier = getattr(signal, "tier", CrisisTier.NONE.value)
        return _CrisisAssessment(is_crisis=tier in veto_tiers, tier=tier, signal=signal)

    def _uwm_directive(uwm) -> str:
        """Plain-language brief from the User World Model's profile/relationship-graph/
        life-context (§7) — never raw scores, matching every other directive in this module.
        communication_model is intentionally not read here: style_learning.py already owns
        communication style live, via the relationship-state directive above."""
        if uwm is None:
            return ""
        parts = []
        p = uwm.profile
        facts = [f for f in (
            p.preferred_name and f"goes by {p.preferred_name}",
            p.current_life_stage if p.current_life_stage != "unknown" else None,
            p.field_of_study_or_work,
            p.institution_or_employer and f"at {p.institution_or_employer}",
        ) if f]
        if facts:
            parts.append("What you know about the user: " + ", ".join(facts) + ".")
        people = sorted(uwm.relationship_graph.people, key=lambda n: n.mention_count, reverse=True)[:3]
        if people:
            names = ", ".join(f"{n.name} ({n.relationship_tier})" for n in people)
            parts.append(f"People who matter to them: {names}.")
        situations = [s.description for s in uwm.life_context.active_situations if s.status == "active"][:2]
        if situations:
            parts.append("Currently going through: " + "; ".join(situations) + ".")
        if not parts:
            return ""
        return (" ".join(parts) + " Weave this in naturally only if relevant — never recite it "
                "back at them or make it sound like you're reading from a file.")

    def _identity_directive(beliefs) -> str:
        """Plain-language brief from Nova's own self-model (§6) — top-centrality non-immutable
        beliefs only. Filters immutable beliefs here too (not just in identity_provider) as
        defense in depth: immutable safety policies are enforced by Layer 11's separate
        hard-coded path, not by reminding the LLM every turn, and must never reach this prompt
        even if some future provider implementation forgets to exclude them itself."""
        mutable = [b for b in (beliefs or []) if not getattr(b, "is_immutable", False)]
        if not mutable:
            return ""
        traits = "; ".join(b.statement for b in mutable)
        return f"This reflects who you (Nova) genuinely are: {traits}. Let it show, don't recite it."

    _MEMORY_POLICY_NOTE = {
        "none": "do not reference specific past conversations at all.",
        "soft": "you may vaguely gesture at past context (\"I remember you mentioned something "
               "like this\") but not cite specific episodes.",
        "episodic": "you may reference specific past episodes directly.",
        "full": "you may reference specific episodes and broader patterns you've noticed.",
    }

    def build_persona(ctx):
        """Per-user Layer-4/5 persona packet: loads the persisted relationship state and turns the
        qualitative stage into a plain-language familiarity directive for the planner prompt."""
        packet = PersonaPacket()
        if relationship_provider is not None:
            try:
                rel = relationship_provider(ctx.user_id)
                if rel is not None:
                    # record_turn (infra/db/relationship_store.py) advances counters + stage but
                    # never stamps the stage-derived behavioral gates (self_disclosure_ceiling,
                    # memory_reference_policy, follow_up_question_ceiling, direct_noticing_allowed)
                    # -- compute_relationship_state does that deterministically from the persisted
                    # state (architecture doc §4.4). No communication_model passed: it's always
                    # None live (Layer 2's UWM narrow slice never extracts one), and passing one
                    # would let _apply_style_calibration overwrite the EMA-learned params
                    # style_learning.py already owns (see docs/POLISH_BACKLOG.md's Layer 4 entry).
                    rel = compute_relationship_state(persisted=rel)
                    packet.relationship_state = rel
                    stage = getattr(rel, "stage", "new")
                    msgs = getattr(rel, "total_messages_exchanged", 0)
                    sessions = getattr(rel, "total_sessions", 0)
                    packet.persona_instruction = (
                        f"You and the user are at the '{stage}' stage of a long-term relationship "
                        f"({msgs} messages across {sessions} sessions). Match that familiarity — "
                        f"warmer and more casual as it deepens; do not over-familiarize when new.")
                    packet.memory_reference_policy = (
                        f"Memory reference policy for this stage: '{rel.memory_reference_policy}' "
                        f"— {_MEMORY_POLICY_NOTE.get(rel.memory_reference_policy, '')}")
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
        if uwm_provider is not None:
            try:
                directive = _uwm_directive(uwm_provider(ctx.user_id))
                if directive:
                    packet.persona_instruction = f"{packet.persona_instruction} {directive}".strip()
            except Exception:
                logger.exception("UWM provider failed; persona without world-model context")
        identity_beliefs = []
        if identity_provider is not None:
            try:
                identity_beliefs = identity_provider(ctx.user_id) or []
                directive = _identity_directive(identity_beliefs)
                if directive:
                    packet.persona_instruction = f"{packet.persona_instruction} {directive}".strip()
            except Exception:
                logger.exception("identity provider failed; persona without self-model context")

        # SC-1 (persona_resolver) + SC-3 (tone_calibrator): real functions, real inputs — identity
        # beliefs above, the relationship state already loaded, and Layer 3's background_state
        # (now live, see docs/layer-3-architecture.md §18). psychological_model/communication_model
        # stay None: the UWM narrow-slice scope (Layer 2 §23) deliberately never extracts either,
        # so there's nothing real to pass yet.
        try:
            persona_state = resolve_persona_state(
                identity_memory_entries=identity_beliefs,
                session_context={"conversation_mode": getattr(ctx, "conversation_mode", "casual")})
            packet.persona_state = persona_state
            constraints = ["Never fabricate emotions or feelings Nova doesn't have.",
                          "Never be sycophantic — disagree when warranted.",
                          "Don't catastrophize."]
            if persona_state.known_sensitivities:
                constraints.append(
                    "Known sensitivities: " + ", ".join(persona_state.known_sensitivities) + ".")
            packet.constraint_instruction = " ".join(constraints)
        except Exception:
            logger.exception("persona_resolver failed; using default PersonaState")
            persona_state = packet.persona_state

        try:
            packet.voice_parameters = calibrate_voice(
                conversation_mode=getattr(ctx, "conversation_mode", "casual"),
                circadian_band=getattr(ctx.input_packet, "circadian_band", "afternoon"),
                relationship_state=packet.relationship_state, persona_state=persona_state,
                background_state=getattr(ctx.emotion_intent, "background_state", None)
                                 or BackgroundEmotionalState())
        except Exception:
            logger.exception("tone_calibrator failed; using default VoiceParameters")
        return packet

    # Layer 7 §6.3 hard blocks: never reference goals in these modes, or before the
    # relationship has moved past first contact. This directive predates SC-4
    # (decide_goal_reference) reaching the live path (its real output is computed
    # post-turn — see POLISH_BACKLOG.md), so the blocks are duplicated here rather than
    # left unenforced.
    _GOAL_BLOCKED_MODES = {"crisis", "emotional_support", "casual"}

    def _goal_directive(ctx) -> str:
        if goal_provider is None:
            return ""
        if getattr(ctx, "conversation_mode", "casual") in _GOAL_BLOCKED_MODES:
            return ""
        stage = getattr(getattr(ctx.persona_packet, "relationship_state", None), "stage", "new")
        if stage == "new":
            return ""
        try:
            titles = [t for t in (goal_provider(ctx.user_id, ctx.message) or []) if t]
        except Exception:
            logger.exception("goal provider failed; no accountability injection this turn")
            return ""
        if not titles:
            return ""
        # §6.4 anti-pattern: never reference more than one goal per response.
        return (f"The user has an active goal: '{titles[0]}'. If it fits naturally, reference "
                f"their progress or gently encourage them — never force it or lecture.")

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
        ei = ctx.emotion_intent
        # SC-4 (drift_detector), pass 1 — role-abandonment (Check 2) and sycophantic-capitulation
        # (Check 3) read only user_message/history, not the draft, so they can and must run
        # BEFORE generation: a role-abandonment request must be refused gracefully by the draft
        # itself, on System 1 turns too (most turns route there) — not silently discarded because
        # only refine() (System 2 only) used to see the directive. `nova_recent_positions` is
        # always [] (no cross-turn stance history tracked yet), so Check 3 never fires in
        # practice; Check 2 works fully without it.
        pre_drift = None
        try:
            pre_drift = detect_drift(
                pending_draft_intent="", user_message=ctx.message,
                persona_state=ctx.persona_packet.persona_state, nova_recent_positions=[])
        except Exception:
            logger.exception("drift_detector (pre-draft) failed; proceeding without a drift check")
        drift_directive = (pre_drift.planner_directive
                          if pre_drift and pre_drift.drift_detected else None)
        directive = " ".join(d for d in (
            _goal_directive(ctx), _elicitation_directive(ctx), drift_directive) if d)
        # Forward the real Layer 2 recall + Layer 3 advice-gate signals that already sit on
        # ctx — previously dropped, so the planner never actually grounded responses in
        # recalled memories despite Layer 2 computing them every turn. See POLISH_BACKLOG.md.
        draft = generate_semantic_draft(
            ctx.message, persona_packet=ctx.persona_packet,
            advice_gate=getattr(ei, "advice_gate", "open"),
            prefers_no_advice=getattr(ei, "prefers_no_advice", False),
            response_instruction=directive,
            recalled_memories=ctx.recalled_memories,
            circadian_band=getattr(ctx.input_packet, "circadian_band", "afternoon"),
            llm_fn=lambda p: client.complete(p))
        # SC-4 pass 2 — re-check against the real draft text so Check 1 (fabricated emotion in
        # the draft) can fire too; stored for refine() (System 2 only) to fold into its own
        # prompt. This is NOT a union with pass 1: detect_drift checks in a fixed priority order
        # (fabrication, then abandonment, then capitulation) and returns on the first hit, so if
        # the draft happens to also trip Check 1 (e.g. contains "I feel"), pass 2's result
        # overwrites pass 1's abandonment finding here even though pass 1's directive already
        # reached the planner prompt above and shaped the draft. What's stored on
        # drift_check_result is "what refine() should react to", not a running log of every
        # check that fired this turn.
        try:
            ctx.persona_packet.drift_check_result = detect_drift(
                pending_draft_intent=draft.text, user_message=ctx.message,
                persona_state=ctx.persona_packet.persona_state, nova_recent_positions=[])
        except Exception:
            logger.exception("drift_detector (post-draft) failed; proceeding without a drift check")
        ctx.semantic_draft_obj = draft
        return draft.text

    def refine(ctx, draft):
        """SC-6 (real emotion_refiner.refine_emotion), not an ad hoc rephrase prompt. `draft` here
        is the plain string plan() returned (the orchestrator's contract); the full SemanticDraft
        (with key_claims, needed for factual-preservation validation) was stashed on ctx by plan()
        just above -- falls back to a claims-less draft if plan() wasn't the real one (e.g. a test
        double), same defensive shape as every other provider lookup in this module."""
        ei = ctx.emotion_intent
        draft_obj = getattr(ctx, "semantic_draft_obj", None) or SemanticDraft(text=draft)
        skip = should_skip_refinement(
            primary_label=getattr(ei.primary_emotion, "primary_label", "neutral"),
            bes_label=getattr(ei.background_state, "bes_label", "insufficient_data"),
            mismatch_detected=getattr(ei.mismatch, "mismatch_detected", False),
            primary_intent=getattr(ei.intent, "primary_intent", "casual_chat"),
            crisis_active=getattr(ei, "crisis_active", False))
        posture = ei.emotional_posture_instruction
        drift = getattr(ctx.persona_packet, "drift_check_result", None)
        if drift is not None and getattr(drift, "drift_detected", False) and drift.planner_directive:
            posture = f"{posture} {drift.planner_directive}"
        result = refine_emotion(
            draft_obj, skip=skip, voice_parameters=ctx.persona_packet.voice_parameters,
            emotional_posture_instruction=posture, persona_packet=ctx.persona_packet,
            primary_emotion_label=getattr(ei.primary_emotion, "primary_label", "neutral"),
            bes_label_description=(getattr(ei.background_state, "trend_note", None)
                                   or getattr(ei.background_state, "bes_label", "")),
            primary_feeling=getattr(ei.empathy_hypothesis, "primary_feeling", ""),
            primary_need=getattr(ei.empathy_hypothesis, "primary_need", ""),
            mismatch_instruction=(getattr(ei, "mismatch_response_posture", "") or ""
                                  if getattr(ei.mismatch, "mismatch_detected", False) else ""),
            llm_fn=lambda p: system2.complete(p))
        return result.final_text

    def social_coaching(ctx, response):
        """SC-4/SC-5, run through the real Layer-5 orchestrator (``build_social_intelligence_
        packet``) instead of reimplementing its detect+inject sequencing here -- that orchestrator
        also owns the LLM observation-regeneration step for PATTERN_REFLECTION/CONFLICT_NAVIGATION
        and the deferred-to-Layer-6 handoff (§8/§9.3 of the architecture doc), which a bare
        detect_coaching_opportunity + inject_observation pair does not. Degrades to a no-op with
        no persisted graph/events/patterns yet, which is the case for every account until the
        background pattern job has run at least once."""
        if social_provider is None:
            return response
        graph, events, patterns = social_provider(ctx.user_id)
        ei = ctx.emotion_intent
        wrapped = FinalResponsePacket(final_text=response)
        packet = build_social_intelligence_packet(
            wrapped, ei,
            social_graph=graph or SocialGraph(user_id=str(ctx.user_id)),
            active_patterns=patterns, events_detected=events,
            relationship_stage=getattr(ctx.persona_packet.relationship_state, "stage", "new"),
            circadian_band=getattr(ctx.input_packet, "circadian_band", "afternoon"),
            voice_parameters=ctx.persona_packet.voice_parameters,
            observation_llm_fn=lambda p: system1.complete(p))
        # Only mark surfaced when the observation was actually delivered this turn (not when
        # injection deferred it for lack of length headroom) -- otherwise gate_3_recency would
        # start blocking a pattern the user never actually saw.
        if packet.coaching_injected and social_surface_writer is not None:
            pattern = packet.coaching_opportunity.triggering_pattern if packet.coaching_opportunity else None
            if pattern is not None:
                try:
                    social_surface_writer(pattern.pattern_id)
                except Exception:
                    logger.exception("social surface writer failed; pattern stays unsurfaced")
        # A deferred opportunity (timing/recency gate, or no length headroom) isn't just dropped --
        # it becomes a durable Layer-6 SOCIAL_PATTERN_COACHING candidate (§9.3) so Nova can raise it
        # later instead of losing it.
        if packet.coaching_deferred and proactive_coaching_writer is not None:
            for opp in packet.proactive_coaching_queue:
                try:
                    proactive_coaching_writer(ctx.user_id, opp)
                except Exception:
                    logger.exception("proactive coaching writer failed; opportunity not queued")
        if packet.coaching_injected and packet.modified_response is not None:
            return packet.modified_response.final_text
        return response

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
        # Forward the two signals that actually change delivered text through this adapter
        # (deliver() only returns final_message_text -- format_spec/micro-interactions/events are
        # not yet consumed here, see POLISH_BACKLOG.md, so there's no point threading signals that
        # only affect the discarded parts of Layer9Output).
        emotional_intensity = getattr(
            getattr(ctx.emotion_intent, "primary_emotion", None), "intensity", 0.0)
        stage = getattr(getattr(ctx.persona_packet, "relationship_state", None), "stage", "new")
        relationship_stage = _LAYER9_STAGE_MAP.get(stage, "friend")
        result = l9_deliver(response, ctx.conversation_mode,
                            crisis_mode_active=crisis_mode_active,
                            emotional_intensity=emotional_intensity,
                            relationship_stage=relationship_stage)
        return getattr(result, "final_message_text", None) or response

    def state_update(ctx):
        if session_writer is not None:
            session_writer(ctx)

    return PipelineSteps(
        perceive=perceive, recall=recall, classify=classify, cold_start=cold_start,
        safety_scan=safety_scan, build_persona=build_persona, tool_use=tool_use,
        plan=plan, refine=refine, social_coaching=social_coaching, guardrails=guardrails,
        escalate=escalate, deliver=deliver, state_update=state_update)
