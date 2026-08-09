"""Layer-6 SC-3/SC-4 delivery machinery, shared between ``GET /proactive`` (gating, real-time)
and ``background/proactive_check_job.py`` (SC-4 message generation, every ~30 min).

Splitting these out of the route means the background job can reuse the exact same timing-gate
construction the route already had, instead of a second, drifting copy of it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.layer6_proactivity.schemas import ProactiveContext, ProactiveItem, UserTimingContext


def build_timing_context(session_factory, uid: str, now: datetime, config: Optional[dict] = None,
                         ) -> UserTimingContext:
    """Assemble a real, live UserTimingContext from the persisted stores (architecture doc §5) --
    the gate has never had a production caller before this pass, so this is the first real
    wiring. User preferences and quiet-period state have no source anywhere in this codebase (no
    preferences store exists) and stay at the gate's own conservative defaults (allow), same
    reasoning as every other genuinely-nothing-to-wire gap in this pass."""
    from backend.layer1_input.temporal_resolver import map_circadian_band
    from backend.layer3_reasoning.background_state import compute_background_state
    from infra.db.memory_store import PostgresMemoryStore
    from infra.db.message_store import PostgresMessageStore
    from infra.db.proactive_store import PostgresProactiveQueue
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.safety_store import PostgresSafetyLog

    tz_offset = (config or {}).get("system", {}).get("timezone_offset_hours", 0.0)
    local_hour = (now + timedelta(hours=tz_offset)).hour
    circadian_band = map_circadian_band(local_hour).value

    last_interaction = PostgresMessageStore(session_factory, uid).last_interaction_at()
    minutes_since = (999 if last_interaction is None
                     else max(0, (now - last_interaction).total_seconds() / 60))

    episodic = PostgresMemoryStore(session_factory).active_episodic(uid)
    bes = compute_background_state(episodic, now=now)
    dated = [m for m in episodic if getattr(m, "created_at", None) is not None]
    last_episode = max(dated, key=lambda m: m.created_at, default=None)
    last_valence = last_episode.emotion_vector.valence if last_episode else 0.0

    rel = PostgresRelationshipStore(session_factory, uid).load()

    recent_safety = PostgresSafetyLog(session_factory).recent(uid, limit=1)
    crisis_flag = bool(recent_safety) and recent_safety[0].tier != "none"

    q = PostgresProactiveQueue(session_factory, uid)
    sent = [i for i in q.load(statuses=["sent", "responded"]) if i.sent_at]
    sent_today = [i for i in sent if i.sent_at.date() == now.date()]
    last_sent = max((i.sent_at for i in sent), default=None)
    hours_since_last = (9999.0 if last_sent is None
                        else (now - last_sent).total_seconds() / 3600)

    return UserTimingContext(
        circadian_band=circadian_band, minutes_since_last_message=int(minutes_since),
        hours_since_last_proactive_message=hours_since_last, last_proactive_sent_at=last_sent,
        proactive_messages_sent_today=len(sent_today), bes_trend=bes.bes_label,
        last_session_crisis_flag=crisis_flag, last_session_end_valence=last_valence,
        relationship_stage=rel.stage, tie_strength=rel.tie_strength)


def gate_passes(item: ProactiveItem, ctx: UserTimingContext, now: datetime) -> bool:
    """True iff SC-2 classification + SC-3 the timing gate approve sending this item right now."""
    from backend.layer6_proactivity.initiative_classifier import classify_initiative
    from backend.layer6_proactivity.timing_gate import evaluate_timing_gate

    session_gap_days = int(ctx.minutes_since_last_message // 1440)
    try:
        classified = classify_initiative(item, bes_trend=ctx.bes_trend,
                                         relationship_stage=ctx.relationship_stage,
                                         session_gap_days=session_gap_days)
        decision = evaluate_timing_gate(item, classified, ctx, now=now)
    except Exception:
        return False          # §11: an unexpected gate error is treated as blocking, not sent
    return decision.action == "send_now"


def _voice_parameters_summary(vp) -> str:
    """Same fields/format as emotion_refiner.build_refiner_prompt's VOICE PARAMETERS block --
    reusing the real Layer-4 VoiceParameters object rather than inventing a second summary shape."""
    return (f"Register: {vp.register}. Warmth: {vp.warmth_expression}. "
           f"Sentence length: {vp.sentence_length}. Max length: "
           f"{vp.max_response_length_chars} characters.")


def build_proactive_context(app_state, item: ProactiveItem, uid: str, now: datetime,
                            ) -> ProactiveContext:
    """Assemble the real SC-4 ProactiveContext by reusing api/assembly.py's build_persona (via
    the live orchestrator's steps) for persona_instruction/voice_parameters/relationship_stage,
    instead of re-deriving them a second time outside a live turn."""
    from types import SimpleNamespace
    from backend.layer1_input.temporal_resolver import map_circadian_band
    from backend.layer3_reasoning.background_state import compute_background_state
    from infra.db.memory_store import PostgresMemoryStore

    mem_store = PostgresMemoryStore(app_state.session_factory)
    episodic = mem_store.active_episodic(uid)
    bes = compute_background_state(episodic, now=now)

    tz_offset = (app_state.config or {}).get("system", {}).get("timezone_offset_hours", 0.0)
    local_hour = (now + timedelta(hours=tz_offset)).hour
    input_packet = SimpleNamespace(circadian_band=map_circadian_band(local_hour).value)
    # build_persona reads ctx.input_packet.circadian_band and ctx.emotion_intent.background_state
    # directly (not getattr-safe on ctx itself) -- both must be present or tone_calibrator
    # silently degrades to default VoiceParameters (caught live: a bare SimpleNamespace without
    # these attributes raised AttributeError inside build_persona's own try/except).
    ctx = SimpleNamespace(user_id=uid, conversation_mode="casual", input_packet=input_packet,
                          emotion_intent=SimpleNamespace(background_state=bes))
    persona_packet = app_state.orchestrator.steps.build_persona(ctx)

    summaries = []
    for mid in (item.source_memory_ids or [])[:3]:
        m = mem_store.get_episodic(mid)
        if m is not None and getattr(m, "summary", ""):
            summaries.append(m.summary)
    if not summaries and item.content_basis:
        summaries = [item.content_basis]

    user_name, life_context = None, ""
    from api.state import make_uwm_provider
    uwm = make_uwm_provider(app_state.session_factory)(uid)
    if uwm is not None:
        user_name = uwm.profile.preferred_name
        situations = [s.description for s in uwm.life_context.active_situations[:3]]
        life_context = "; ".join(situations)

    return ProactiveContext(
        source_memory_summaries=summaries,
        source_goal_summary=item.content_basis if item.source_goal_id else None,
        user_name_if_known=user_name,
        current_life_context=life_context,
        bes_trend_description=bes.trend_note or bes.bes_label,
        persona_instruction=persona_packet.persona_instruction,
        relationship_stage=getattr(persona_packet.relationship_state, "stage", "developing"),
        voice_parameters_summary=_voice_parameters_summary(persona_packet.voice_parameters),
    )


def generate_message_for_item(app_state, item: ProactiveItem, uid: str, now: datetime,
                              ) -> Optional[str]:
    """Run the real SC-2 classification + SC-4 message generation for one gate-passing item.
    Returns the generated text, or None if generation/validation failed (§11: no fallback
    message — the item just stays without one and is reconsidered next job run)."""
    from backend.layer6_proactivity.initiative_classifier import classify_initiative
    from backend.layer6_proactivity.message_generator import generate_proactive_message

    llm = (app_state.llm_clients or {}).get("system1")
    if llm is None:
        return None
    ctx = build_timing_context(app_state.session_factory, uid, now, app_state.config)
    session_gap_days = int(ctx.minutes_since_last_message // 1440)
    classified = classify_initiative(item, bes_trend=ctx.bes_trend,
                                     relationship_stage=ctx.relationship_stage,
                                     session_gap_days=session_gap_days)
    proactive_ctx = build_proactive_context(app_state, item, uid, now)
    payload = generate_proactive_message(
        item, classified, proactive_ctx, user_id=uid,
        llm_fn=lambda p: llm.complete(p), now=now)
    return payload.message_text if payload is not None else None
