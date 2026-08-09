"""Proactivity routes — poll the Layer-6 outreach queue (single-user).

No push channel without a frontend, so a client polls this for the current top candidates; the
scheduler's proactive-check job keeps the queue prioritized and pruned. Candidates are gated
server-side through the real SC-3 Timing & Delivery Gate (``evaluate_timing_gate``) before being
returned — a future frontend rendering ``content_basis`` directly as a Nova message can no longer
bypass the gate's five block groups just by reading this endpoint.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import ProactiveItemOut
from infra.db.proactive_store import PostgresProactiveQueue

router = APIRouter(prefix="/proactive", tags=["proactive"])


def _build_timing_context(state, uid: str, now: datetime):
    """Assemble a real, live UserTimingContext from the persisted stores (architecture doc §5) --
    the gate has never had a production caller before, so this is the first real wiring. User
    preferences and quiet-period state have no source anywhere in this codebase (no preferences
    store exists) and stay at the gate's own conservative defaults (allow), same reasoning as
    every other genuinely-nothing-to-wire gap in this pass."""
    from backend.layer1_input.temporal_resolver import map_circadian_band
    from backend.layer3_reasoning.background_state import compute_background_state
    from backend.layer6_proactivity.schemas import UserTimingContext
    from infra.db.memory_store import PostgresMemoryStore
    from infra.db.message_store import PostgresMessageStore
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.safety_store import PostgresSafetyLog

    tz_offset = (state.config or {}).get("system", {}).get("timezone_offset_hours", 0.0)
    local_hour = (now + timedelta(hours=tz_offset)).hour
    circadian_band = map_circadian_band(local_hour).value

    last_interaction = PostgresMessageStore(state.session_factory, uid).last_interaction_at()
    minutes_since = (999 if last_interaction is None
                     else max(0, (now - last_interaction).total_seconds() / 60))

    episodic = PostgresMemoryStore(state.session_factory).active_episodic(uid)
    bes = compute_background_state(episodic, now=now)
    dated = [m for m in episodic if getattr(m, "created_at", None) is not None]
    last_episode = max(dated, key=lambda m: m.created_at, default=None)
    last_valence = last_episode.emotion_vector.valence if last_episode else 0.0

    rel = PostgresRelationshipStore(state.session_factory, uid).load()

    recent_safety = PostgresSafetyLog(state.session_factory).recent(uid, limit=1)
    crisis_flag = bool(recent_safety) and recent_safety[0].tier != "none"

    q = PostgresProactiveQueue(state.session_factory, uid)
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


@router.get("", response_model=list[ProactiveItemOut])
def list_proactive(limit: int = 5, state=Depends(get_state)):
    from backend.layer6_proactivity.initiative_classifier import classify_initiative
    from backend.layer6_proactivity.timing_gate import evaluate_timing_gate

    uid = state.default_user_id
    now = datetime.now(timezone.utc)
    try:
        items = PostgresProactiveQueue(state.session_factory, uid).load(
            statuses=["pending", "deferred"])
        ctx = _build_timing_context(state, uid, now)
    except Exception:
        raise HTTPException(status_code=503, detail="proactive queue unavailable")

    session_gap_days = int(ctx.minutes_since_last_message // 1440)
    approved = []
    for i in items:
        try:
            classified = classify_initiative(i, bes_trend=ctx.bes_trend,
                                             relationship_stage=ctx.relationship_stage,
                                             session_gap_days=session_gap_days)
            decision = evaluate_timing_gate(i, classified, ctx, now=now)
        except Exception:
            continue      # §11: an unexpected gate error is treated as blocking, not sent
        if decision.action == "send_now":
            approved.append(i)

    approved.sort(key=lambda i: getattr(i, "current_priority", 0.0), reverse=True)
    return [ProactiveItemOut(
        item_id=i.item_id, item_type=i.item_type, status=i.status,
        content_basis=getattr(i, "content_basis", "") or "",
        current_priority=float(getattr(i, "current_priority", 0.0) or 0.0))
        for i in approved[:limit]]
